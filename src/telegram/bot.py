# coding: utf-8

import asyncio
import importlib
import os
import pkgutil

from aiogram import Bot, Dispatcher
from aiogram.types import (BotCommand, BotCommandScopeAllGroupChats,
                           BotCommandScopeDefault)
from loguru import logger
from pydantic import SecretStr

import utils
from api import (TelehooperAPI, TelehooperGroup, TelehooperSubGroup,
                 TelehooperUser)
from config import config
from consts import COMMANDS, COMMANDS_USERS_GROUPS
from DB import get_db
from services.service_api_base import ServiceDisconnectReason
from services.vk.exceptions import TokenRevokedException
from services.vk.service import VKServiceAPI


bot = Bot(
	token=config.telegram_token.get_secret_value(),
	parse_mode="HTML"
)
dispatcher = Dispatcher()

def get_bot() -> Bot:
	"""
	Возвращает экземпляр Telegram-бота.
	"""

	return bot

def get_dispatcher() -> Dispatcher:
	"""
	Возвращает экземпляр Dispatcher.
	"""

	return dispatcher

def init_handlers() -> None:
	"""
	Инициализирует все Handler'ы, Router'ы бота, находящиеся в папке `handlers` и `middlewares`.
	"""

	logger.debug("Загружаю все handler'ы для Telegram-бота...")

	for _, module_name, _ in pkgutil.iter_modules([os.path.join(os.path.dirname(__file__), "handlers")]):
		logger.debug(f"Запускаю handler'ы из модуля {module_name}...")

		# Пытаемся инициализировать модуль.
		try:
			module = importlib.import_module(f"telegram.handlers.{module_name}")
		except Exception as error:
			logger.exception(f"Не удалось загрузить handler'ы из модуля {module_name}:", error)

			continue
		else:
			if "router" not in dir(module):
				raise Exception(f"Модуль {module_name} не содержит переменную 'router'.")

			dispatcher.include_router(module.router)

	logger.debug("Загружаю все middleware'ы для Telegram-бота")

async def set_commands(use_async: bool = True) -> None:
	"""
	Устанавливает команды для бота.

	:param use_async: Асинхронная установка команд.
	"""

	async def _set_commands() -> None:
		# TODO: Поддержка языков.

		await bot.set_my_commands(
			commands=[
				BotCommand(
					command=command,
					description=description
				) for command, description in COMMANDS.items()
			],
			scope=BotCommandScopeDefault(
				type="default"
			)
		)

		await bot.set_my_commands(
			commands=[
				BotCommand(
					command=command,
					description=description
				) for command, description in COMMANDS_USERS_GROUPS.items()
			],
			scope=BotCommandScopeAllGroupChats(
				type="all_group_chats"
			)
		)

	if use_async:
		asyncio.create_task(_set_commands())
	else:
		await _set_commands()

async def reconnect_services(use_async: bool = True) -> None:
	"""
	Переподключает сервисы.

	:param use_async: Асинхронное переподключение.
	"""

	async def _reconnect_services() -> None:
		db = await get_db()

		async for user in db.docs(prefix="user_"):
			telegram_user = (await bot.get_chat_member(user["ID"], user["ID"])).user
			telehooper_user = TelehooperUser(user, telegram_user)
			service_apis = {}

			logger.debug(f"Переподключаю сервисы и диалоги Telegram-пользователя {utils.get_telegram_logging_info(telegram_user)}...")

			# Переподключаем сервисы.
			try:
				if "VK" in user["Connections"]:
					vkServiceAPI = None

					# Проверка, что токен установлен.
					# Токен может отсутствовать, если настройка Security.
					if not user["Connections"]["VK"]["Token"]:
						# Удаляем сервис из БД.
						user["Connections"].pop("VK")
						await user.save()

						# Отправляем сообщение.
						await bot.send_message(
							chat_id=user["ID"],
							text=(
								"<b>⚠️ Потеряно соединение с ВКонтакте</b>.\n"
								"\n"
								"Telehooper потерял соединение со страницей «ВКонтакте», поскольку настройка <i>⚙️ Хранение токенов в БД</i> (<code>/s Security.StoreTokens</code>) была выставлена в значение «выключено».\n"
								"\n"
								"ℹ️ Вы можете повторно подключиться к «ВКонтакте», используя команду /connect.\n"
							)
						)

						continue

					# Создаём Longpoll.
					try:
						vkServiceAPI = VKServiceAPI(
							token=SecretStr(
								utils.decrypt_with_env_key(
									user["Connections"]["VK"]["Token"]
								)
							),
							vk_user_id=user["Connections"]["VK"]["ID"],
							user=telehooper_user
						)
						telehooper_user.save_connection(vkServiceAPI)

						# Проверяем токен.
						await vkServiceAPI.vkAPI.get_self_info()

						# Запускаем Longpoll.
						await vkServiceAPI.start_listening()

						# Сохраняем ServiceAPI.
						service_apis["VK"] = vkServiceAPI
					except TokenRevokedException as error:
						assert vkServiceAPI

						# Совершаем отключение.
						await vkServiceAPI.disconnect_service(ServiceDisconnectReason.ERRORED)

						# Отправляем сообщение.
						await bot.send_message(
							chat_id=user["ID"],
							text=(
								"<b>⚠️ Потеряно соединение с ВКонтакте</b>.\n"
								"\n"
								"Telehooper потерял соединение со страницей «ВКонтакте», поскольку владелец страницы отозвал доступ к ней через настройки «Приватности» страницы.\n"
								"\n"
								"ℹ️ Вы можете повторно подключиться к «ВКонтакте», используя команду /connect.\n"
							)
						)
					except Exception as error:
						logger.exception(f"Не удалось запустить LongPoll для пользователя {user['ID']}:", error)

						# В некоторых случаях, сам объект VKServiceAPI может быть None,
						# например, если не удалось расшифровать токен.
						# В таких случаях нам необходимо сделать отключение, при помощи
						# фейкового объекта VKServiceAPI.
						if vkServiceAPI is None:
							vkServiceAPI = VKServiceAPI(
								token=None, # type: ignore
								vk_user_id=user["Connections"]["VK"]["ID"],
								user=telehooper_user
							)

						# Совершаем отключение.
						await vkServiceAPI.disconnect_service(ServiceDisconnectReason.ERRORED)

						# Отправляем сообщение.
						await bot.send_message(
							chat_id=user["ID"],
							text=(
								"<b>⚠️ Произошла ошибка при работе с ВКонтакте</b>.\n"
								"\n"
								"К сожалению, ввиду ошибки бота, у Telehooper не удалось востановить соединение с Вашей страницей «ВКонтакте».\n"
								"Вы не сможете отправлять или получать сообщения из этого сервиса до тех пор, пока Вы не переподключитесь к нему.\n"
								"\n"
								"ℹ️ Вы можете повторно подключиться к сервису «ВКонтакте», используя команду /connect.\n"
							)
						)
			except Exception as error:
				logger.exception(f"Не удалось переподключить сервисы для пользователя {user['ID']}:", error)

				continue

			# Все сервисы переподключены, возвращаем диалоги.
			async for group in db.docs([f"group_{i}" for i in user["Groups"]]):
				telegram_group = await bot.get_chat(group["ID"])
				telehooper_group = TelehooperGroup(telehooper_user, group, telegram_group, bot)

				for chat in group["Chats"].values():
					serviceAPI = service_apis.get(chat["Service"])

					if not serviceAPI:
						continue

					TelehooperAPI.save_subgroup(
						TelehooperSubGroup(
							id=chat["ID"],
							dialogue_name=chat["Name"],
							service=serviceAPI,
							parent=telehooper_group,
							service_chat_id=chat["DialogueID"]
						)
					)
	if use_async:
		asyncio.create_task(_reconnect_services())
	else:
		await _reconnect_services()

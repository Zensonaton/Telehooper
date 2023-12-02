# coding: utf-8

import asyncio
import importlib
import os
import pkgutil
import re
from types import ModuleType
from typing import Tuple, cast

from aiocouch import Document
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (BotCommand, BotCommandScopeAllGroupChats,
                           BotCommandScopeDefault)
from loguru import logger

import utils
from api import (TelehooperAPI, TelehooperGroup, TelehooperSubGroup,
                 TelehooperUser)
from config import config
from consts import COMMANDS, COMMANDS_USERS_GROUPS
from DB import get_db
from services.vk.service import VKServiceAPI


bot = Bot(
	token=config.telegram_token.get_secret_value(),
	parse_mode="HTML"
)
dispatcher = Dispatcher()
username: str | None

minibots: dict[str, Bot] = {}

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

def get_minibots() -> dict[str, Bot]:
	"""
	Возвращает словарь всех подключённых миниботов.
	"""

	return minibots

def init_handlers() -> None:
	"""
	Инициализирует все Handler'ы, Router'ы бота, находящиеся в папке `handlers` и `middlewares`.
	"""

	logger.debug("Загружаю все handler'ы для Telegram-бота...")

	imported_modules: list[ModuleType] = []
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

			imported_modules.append(module)

	# Сортируем модули по приоритету.
	imported_modules.sort(key=lambda x: getattr(x, "_priority_", 0), reverse=True)

	# Инициализируем Router'ы.
	for module in imported_modules:
		dispatcher.include_router(module.router)

	logger.debug("Загружаю middleware...")

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

async def reconnect_services() -> None:
	"""
	Переподключает сервисы у пользователей бота.
	"""

	db = await get_db()
	tasks = []

	async def _reconnect(user: Document) -> None:
		"""
		Функция для `asyncio.Task`, которая переподключает пользователя.
		"""

		try:
			telegram_user = (await bot.get_chat_member(user["ID"], user["ID"])).user
		except TelegramBadRequest:
			logger.error(f"Боту не удалось получить информацию о Telegram-пользователе с ID {user['ID']}, поэтому данный пользователь будет помечен как BotBanned.")

			user["BotBanned"] = True
			await user.save()

			return

		telehooper_user = TelehooperUser(user, telegram_user)
		service_apis = {}

		logger.debug(f"Переподключаю сервисы и диалоги Telegram-пользователя {utils.get_telegram_logging_info(telegram_user)}...")

		# Переподключаем сервисы у пользователя.
		try:
			if "VK" in user["Connections"]:
				service_apis["VK"] = await VKServiceAPI.reconnect_on_restart(telehooper_user, user, bot)
		except Exception as error:
			logger.exception(f"Не удалось переподключить сервисы для пользователя {user['ID']}:", error)

			return

		# Все сервисы переподключены, возвращаем диалоги.
		try:
			for group in await telehooper_user.get_connected_groups(bot=bot):
				try:
					for chat in group.chats.values():
						serviceAPI = service_apis.get(chat["Service"])

						if not serviceAPI:
							continue

						TelehooperAPI.save_subgroup(
							TelehooperSubGroup(
								id=chat["ID"],
								dialogue_name=chat["Name"],
								service=serviceAPI,
								parent=group,
								service_chat_id=chat["DialogueID"]
							)
						)
				except (TelegramForbiddenError, TelegramBadRequest):
					logger.debug(f"Удаляю Telegram-группу {group.chat.id} для пользователя {utils.get_telegram_logging_info(telegram_user)}, поскольку бот не смог получить о ней информацию.")

					await TelehooperAPI.delete_group_data(group.chat.id, fully_delete=True, bot=bot)
				except Exception as error:
					logger.exception(f"Не удалось переподключить группу {group.chat.id} для пользователя {utils.get_telegram_logging_info(telegram_user)}:", error)
		except Exception as error:
			logger.exception(f"Не удалось переподключить диалоги для пользователя {user['ID']}:", error)

			return

	async for user in db.docs(prefix="user_"):
		if user["BotBanned"]:
			continue

		tasks.append(asyncio.create_task(_reconnect(user)))

	await asyncio.gather(*tasks)

async def connect_minibots(session: BaseSession) -> dict[str, Bot]:
	"""
	Подключает миниботов. В данном методе polling для таких ботов не запускается.

	Возвращает словарь объектов класса `Bot` подключённых ботов, где ключ - @username, а значение - сам объект класса `Bot`.

	После подключения, можно воспользоваться методом `get_minibots()` для извлечения списка всех подключённых миниботов.
	"""

	global minibots

	async def _connect(token: str) -> Bot:
		"""
		Функция для `asyncio.Task`, которая делает проверки, связанные с указанным токеном минибота.
		"""

		minibot = Bot(
			token,
			session=session,
			parse_mode="HTML"
		)
		username = (await minibot.get_me()).username
		assert username, "Для минибота не был получен @username"

		logger.debug(f"Username для бота {minibot.id}: @{username}")
		minibots[username] = minibot

		return minibot

	tasks = [_connect(token) for token in utils.get_minibot_tokens()]
	await asyncio.gather(*tasks)

	# Делаем сортированную версию словаря, что бы @username'ы ботов были в правильном порядке.
	minibots = dict(sorted(minibots.items(), key=lambda item: [int(s) if s.isdigit() else s.lower() for s in re.split(r"([0-9]+)", item[0])]))

	return minibots

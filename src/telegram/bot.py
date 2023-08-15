# coding: utf-8

import asyncio
import importlib
import os
import pkgutil
from types import ModuleType
from aiocouch import Document

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
username: str | None

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

	from telegram.middlewares.ratelimitretry import RetryRequestMiddleware

	dispatcher.message.middleware(RetryRequestMiddleware())
	dispatcher.callback_query.middleware(RetryRequestMiddleware())

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

		telegram_user = (await bot.get_chat_member(user["ID"], user["ID"])).user
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

	async for user in db.docs(prefix="user_"):
		tasks.append(asyncio.create_task(_reconnect(user)))

	await asyncio.gather(*tasks)

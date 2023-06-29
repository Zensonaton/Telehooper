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
from config import config
from consts import COMMANDS, COMMANDS_USERS_GROUPS
from DB import get_db
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

			if "VK" in user["Connections"]:
				await VKServiceAPI(
					token=SecretStr(
						utils.decryptWithEnvKey(
							user["Connections"]["VK"]["Token"]
						)
					),
					user=telegram_user
				).start_listening()

	if use_async:
		asyncio.create_task(_reconnect_services())
	else:
		await _reconnect_services()

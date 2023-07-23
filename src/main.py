# coding: utf-8

import asyncio

from loguru import logger

from config import config
from DB import get_db
from logger import init_logger
from telegram import bot


async def bot_init() -> None:
	"""
	Функция, инициализирующая полностью Telehooper-бота.
	"""

	# Логирование.
	init_logger(debug=config.debug)

	logger.info("Привет, мир! Запускаем Telehooper...")

	# Проверяем на debug-режим.
	if config.debug:
		logger.warning("Вы запустили Telehooper в debug-режиме!")
		logger.warning("Debug-режим используется ТОЛЬКО во время разработки бота.")
		logger.warning("Если Вы являетесь обычным пользователем, то пожалуйста, перезапустите бота без debug-режима, удалив поле \"debug\" в Вашем файле \".env\".")
		logger.warning("В Debug-режиме, у пользователей без роли \"tester\" не будет возможности пользоваться ботом.")

	# CouchDB.
	logger.info("Пытаюсь подключиться к базе данных CouchDB...")
	await get_db(check_auth=True)

	# Инициализируем Router'ы.
	logger.info("Подготавливаюсь к запуску бота...")
	bot.init_handlers()

	# Восстанавливаем сессии сервисов.
	logger.info("Восстанавливаю сессии сервисов...")
	await bot.reconnect_services()

	# Узнаём username бота.
	bot_me = await bot.bot.get_me()
	bot.username = bot_me.username

	logger.debug(f"Username бота: @{bot.username}.")

	# Устанавливаем команды.
	await bot.set_commands()

	# Запускаем самого Telegram-бота.
	logger.info("Все проверки перед запуском прошли успешно! Запускаем Telegram-бота...")
	await bot.bot.delete_webhook(drop_pending_updates=True)
	await bot.dispatcher.start_polling(bot.bot, allowed_updates=bot.dispatcher.resolve_used_update_types())

# Запускаем бота.
if __name__ == "__main__":
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	# Запускаем.
	loop.run_until_complete(bot_init())

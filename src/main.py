# coding: utf-8

import asyncio

from loguru import logger

from config import config
from DB import get_db
from logger import init_logger
from telegram import bot


async def bot_init() -> None:
	"""
	Функция, запускающаяся ПОСЛЕ запуска Telegram-бота.
	"""

	# Логирование.
	init_logger(debug=config.debug)

	logger.info("Привет, мир! Запускаем Telehooper...")

	# CouchDB.
	logger.info("Пытаюсь подключиться к базе данных CouchDB...")
	await get_db(check_auth=True)

	# Инициализируем Router'ы.
	logger.info("Подготавливаюсь к запуску бота...")
	bot.init_handlers()

	# Восстанавливаем сессии сервисов.
	logger.info("Восстанавливаю сессии сервисов...")
	await bot.reconnect_services()

	# Устанавливаем команды.
	await bot.set_commands()

	# Бот.
	logger.info("Все проверки перед запуском прошли успешно! Запускаем Telegram-бота...")
	await bot.dispatcher.start_polling(
		bot.bot,
		allowed_updates=bot.dispatcher.resolve_used_update_types()
	)

# Запускаем бота.
if __name__ == "__main__":
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	# Запускаем.
	loop.run_until_complete(bot_init())

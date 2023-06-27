# coding: utf-8

import asyncio

from loguru import logger
from telegram import bot
from logger import init_logger
from config import config

from DB import get_db


async def bot_init() -> None:
	"""
	Функция, запускающаяся ПОСЛЕ запуска Telegram-бота.
	"""

	# Логирование.
	init_logger(debug=config.debug)

	logger.info("Привет, мир! Запускаем Telehooper...")

	# Инициализируем Router'ы.
	logger.info("Подготавливаюсь к запуску бота...")
	bot.init_handlers()

	# Устанавливаем команды.
	await bot.set_commands()

	# CouchDB.
	logger.info("Пытаюсь подключиться к базе данных CouchDB...")
	await get_db(check_auth=True)

	# Бот.
	logger.info("Все проверки перед запуском прошли успешно! Запускаем Telegram-бота...")
	await bot.dispatcher.start_polling(bot.bot)

# Запускаем бота.
if __name__ == "__main__":
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	# Запускаем.
	loop.run_until_complete(bot_init())

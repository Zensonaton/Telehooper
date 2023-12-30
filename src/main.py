# coding: utf-8

import asyncio

from loguru import logger

import utils
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

	logger.info(f"Привет, мир! Запускаем Telehooper commit {await utils.get_commit_hash() or '<неизвестно>'} {'с Local Bot API' if utils.is_local_bot_api() else ''}...")

	# Проверяем на debug-режим.
	if config.debug:
		logger.warning("Вы запустили Telehooper в debug-режиме!")
		logger.warning("Debug-режим используется ТОЛЬКО во время разработки бота.")
		logger.warning("Если Вы являетесь обычным пользователем, то пожалуйста, перезапустите бота без debug-режима, удалив поле \"debug\" в Вашем файле \".env\".")
		logger.warning("В Debug-режиме, у пользователей без роли \"tester\" не будет возможности пользоваться ботом.")

	# Если у нас release, проверяем подключение к CouchDB.
	if not config.debug:
		logger.info("Пытаюсь подключиться к базе данных CouchDB...")
		await get_db(check_auth=True)

	# Проверяем, что у нас указан путь к ffmpeg.
	if not config.ffmpeg_path:
		logger.warning("Вы не указали путь к ffmpeg!")
		logger.warning("Не указав путь к ffmpeg, Telehooper не сможет пересылать GIF из Telegram как GIF в других сервисах.")

	# Инициализируем Router'ы.
	logger.info("Подготавливаюсь к запуску бота...")
	bot.init_handlers()

	# Узнаём username бота.
	bot_me = await bot.bot.get_me()
	bot.username = bot_me.username

	logger.debug(f"Username главного бота: @{bot.username}.")

	# Подключаем миниботов.
	logger.info(f"Подключаю миниботов...")
	await bot.connect_minibots(bot.bot.session)

	logger.info(f"Успешно подключено {len(bot.get_minibots())} миниботов.")

	# Восстанавливаем сессии сервисов.
	logger.info("Восстанавливаю сессии сервисов...")
	await bot.reconnect_services()

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

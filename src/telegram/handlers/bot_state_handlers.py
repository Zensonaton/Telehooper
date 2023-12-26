# coding: utf-8

from aiogram import Bot, Router
from loguru import logger

from api import TelehooperAPI
from telegram.handlers.status import get_bot_status_fields
from utils import get_commit_hash


router = Router()

@router.startup()
async def bot_startup_handler(bot: Bot) -> None:
	"""
	Handler для события запуска бота.

	Логирует, а так же отправляет сообщение о запуске бота в ЛС тем пользователям, у которых есть роль `logBotState`.
	"""

	logger.info("Telegram-бот был успешно запущен.")

	# Получаем список пользователей с ролью "logBotState", игнорируя роль "*", если таковая есть.
	admin_users = await TelehooperAPI.get_users_with_role("logBotState", allow_any=False)

	for user_id in admin_users:
		try:
			await bot.send_message(
				chat_id=user_id,
				text=(
					"<b>🟢 Включение бота</b>.\n"
					"\n"
					f"Commit hash: <code>{await get_commit_hash()}</code>."
				),
				disable_notification=True
			)
		except:
			pass

@router.shutdown()
async def bot_shutdown_handler(bot: Bot) -> None:
	"""
	Handler для события отключения бота.

	Логирует, а так же отправляет сообщение о выключении бота в ЛС тем пользователям, у которых есть роль `logBotState`.
	"""

	bot_state = await get_bot_status_fields()

	logger.info("Telegram-бот отключается. Состояние перед выключением:")
	logger.info(bot_state)

	# Получаем список пользователей с ролью "logBotState".
	admin_users = await TelehooperAPI.get_users_with_role("logBotState", allow_any=False)

	for user_id in admin_users:
		try:
			await bot.send_message(
				chat_id=user_id,
				text=(
					"<b>🔴 Отключение бота</b>.\n"
					"\n"
					"Состояние бота перед отключением:\n"
					f"{bot_state}"
				),
				disable_notification=True
			)
		except:
			pass


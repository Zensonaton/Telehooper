# coding: utf-8

"""Handler для команды `Debug`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `Debug`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(Debug, commands=["debug"])


async def Debug(msg: MessageType):
	logger.info(f"Пользователь {msg.from_user.id} вызвал команду Debug!")

	await msg.answer("HI!", disable_notification=True)

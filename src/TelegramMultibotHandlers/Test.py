# coding: utf-8

"""Обработчик для команды `Test`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot, mainBot: Bot):
	"""
	Инициализирует команду `Test`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(Test, commands=["test"])


async def Test(msg: MessageType):
	logger.info(f"Пользователь {msg.from_user.id} вызвал команду Test!")

	await msg.answer("Hi!")

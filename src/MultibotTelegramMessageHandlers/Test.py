# coding: utf-8

"""Handler для команды `Test`."""

from aiogram.types import Message as MessageType
from aiogram import Dispatcher, Bot
import logging

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

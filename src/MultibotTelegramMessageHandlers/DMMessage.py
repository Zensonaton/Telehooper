# coding: utf-8

"""Handler для команды `DMMessage`."""

from aiogram.types import Message as MessageType
from aiogram import Dispatcher, Bot
import logging

BOT: Bot = None  # type: ignore
MAIN_BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot, mainBot: Bot):
	"""
	Инициализирует команду `DMMessage`.
	"""

	global BOT, MAIN_BOT

	BOT = bot
	MAIN_BOT = mainBot
	dp.register_message_handler(DMMessage, lambda msg: msg.chat.type == "private")


async def DMMessage(msg: MessageType):
	await msg.answer(f"<b>Привет!</b> 🙋‍♀️\nЭтот бот не делает ничего в личных сообщениях; Я являюсь частью основного бота, {(await MAIN_BOT.get_me()).get_mention()}.")

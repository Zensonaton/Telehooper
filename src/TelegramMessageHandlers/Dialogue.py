# coding: utf-8

"""Handler для команды `ThisDialogue`."""

from aiogram.types import Message as MessageType
from aiogram import Dispatcher, Bot
import logging

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `ThisDialogue`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(ThisDialogue, commands=["thisdialogue", "dialogue"])


async def ThisDialogue(msg: MessageType):
	await msg.answer("Команда для управления диалогом.")

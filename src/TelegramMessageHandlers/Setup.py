# coding: utf-8

"""Handler для команды `Setup`."""

from aiogram.types import Message as MessageType
from aiogram import Dispatcher, Bot
import logging

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `Setup`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(Setup, commands=["setup"])


async def Setup(msg: MessageType):
	await msg.answer("Выбери нужный тебе сервис, который необходимо подключить к боту. В данный момент поддерживается лишь <b>ВКонтакте</b>, однако, в будущем планируется больше!\nЕсли у тебя есть знания Python и ты хочешь помочь, то дорога в <a href=\"https://github.com/Zensonaton/Telehooper\">Github проекта</a> открыта! 👀\n\n⚙️ Выбери сервис:")

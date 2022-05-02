# coding: utf-8

"""Handler для команды `Start`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `Start`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(Start, commands=["start"])


async def Start(msg: MessageType):
	await msg.answer("<b>Привет! 🙋</b>\n\nЯ — бот с <a href=\"https://github.com/Zensonaton/Telehooper\">открытым исходным кодом</a>, позволяющий <b>отправлять</b> и <b>получать</b> сообщения из ВКонтакте напрямую в Telegram.\nДля продолжения, воспользуйся командой /setup.")

# coding: utf-8

"""Обработчик для команды `Start`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `Start`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(Start, commands=["start", "help"])


async def Start(msg: MessageType) -> None:
	await msg.answer("<b>Привет! 🙋</b>\n\nЯ — бот с <a href=\"https://github.com/Zensonaton/Telehooper\">открытым исходным кодом</a>, позволяющий <b>отправлять</b> и <b>получать</b> сообщения из ВКонтакте напрямую в Telegram.\nДля продолжения, воспользуйся командой /setup.")

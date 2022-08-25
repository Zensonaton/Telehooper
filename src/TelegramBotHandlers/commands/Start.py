# coding: utf-8

"""Обработчик для команды `Start`."""

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger
from TelegramBot import Telehooper

TelehooperBot: 	Telehooper 	= None # type: ignore
TGBot: 			Bot 		= None # type: ignore
DP: 			Dispatcher 	= None # type: ignore


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `Start`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(Start, commands=["start"])


async def Start(msg: MessageType) -> None:
	await msg.answer("<b>Привет! 🙋\n\n</b>Я — бот с <a href=\"https://github.com/Zensonaton/Telehooper\">открытым исходным кодом</a>, позволяющий <b>отправлять</b> и <b>получать</b> сообщения из <b>ВКонтакте</b> напрямую в Telegram. 🤖\n\n⚙️ Для продолжения воспользуйся командой /self.")

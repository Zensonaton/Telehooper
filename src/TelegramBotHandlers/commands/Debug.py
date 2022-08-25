# coding: utf-8

# TODO: Удалить этот Handler.

"""Обработчик для команды `Debug`."""

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger
from TelegramBot import Telehooper

TelehooperBot: 	Telehooper 	= None # type: ignore
TGBot: 			Bot 		= None # type: ignore
DP: 			Dispatcher 	= None # type: ignore


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `Debug`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(Debug, commands=["debug"])


async def Debug(msg: MessageType) -> None:
	newline = "\n"
	newlinestr = "\\n"

	text = msg.html_text
	if msg.reply_to_message:
		text = msg.reply_to_message.html_text


	await msg.answer(f"<code>{text.replace('<', '&lt;').replace(newline, newlinestr)}</code>")

# coding: utf-8

"""Обработчик для команды `MD`."""

from typing import TYPE_CHECKING

from aiogram import Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger

if TYPE_CHECKING:
	from TelegramBot import Telehooper

TELEHOOPER:	"Telehooper" = None # type: ignore
DP: 		Dispatcher   = None # type: ignore


def _setupHandler(bot: "Telehooper") -> None:
	"""
	Инициализирует Handler.
	"""

	global TELEHOOPER, DP

	TELEHOOPER = bot
	DP = TELEHOOPER.DP

	DP.register_message_handler(MD, commands=["md"])


async def MD(msg: MessageType) -> None:
	newline = "\n"
	newlinestr = "\\n"

	text = msg.html_text
	if msg.reply_to_message:
		text = msg.reply_to_message.html_text


	text = text.replace('<', '&lt;').replace(newline, newlinestr).replace('"', '\\"')
	await msg.answer(f"<code>{text}</code>")

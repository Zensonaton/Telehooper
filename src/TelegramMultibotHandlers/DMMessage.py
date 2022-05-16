# coding: utf-8

"""Обработчик для команды `DMMessage`."""

import logging
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType

if TYPE_CHECKING:
	from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper):
	"""
	Инициализирует команду `DMMessage`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(DMMessage, lambda msg: msg.chat.type == "private")


async def DMMessage(msg: MessageType):
	await msg.answer(f"<b>Привет!</b> 🙋‍♀️\n\nЭтот бот не делает ничего в личных сообщениях, этот бот является частью основного бота, {(await TGBot.get_me()).mention}.")

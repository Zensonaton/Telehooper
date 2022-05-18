# coding: utf-8

"""Обработчик для команды `Debug`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper):
	"""
	Инициализирует команду `Debug`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP
	
	DP.register_message_handler(Debug, commands=["debug"])


async def Debug(msg: MessageType):
	# Команда используется для debugging'а.

	user = await Bot.getBotUser(msg.from_user.id)

	await msg.answer("Привет, мир!")

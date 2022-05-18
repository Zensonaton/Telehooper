# coding: utf-8

"""Обработчик для команды `Connect`."""

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
	Инициализирует команду `Connect`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP
	
	DP.register_message_handler(Connect, commands=["connect"])


async def Connect(msg: MessageType):
	await msg.answer("Привет, мир!")

# coding: utf-8

"""Обработчик для команды `Test`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from TelegramBot import Telehooper

TelehooperBot: 	Telehooper 	= None # type: ignore
TGBot: 			Bot 		= None # type: ignore
DP: 			Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)

def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `Test`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(Test, commands=["test"])


async def Test(msg: MessageType) -> None:
	logger.info(f"Пользователь {msg.from_user.id} вызвал команду Test!")

	await msg.answer("Hi!")

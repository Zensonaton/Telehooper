# coding: utf-8

"""Обработчик для команды `DMMessage`."""

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger
from TelegramBot import Telehooper

TelehooperBot: 	Telehooper 	= None # type: ignore
TGBot: 			Bot 		= None # type: ignore
DP: 			Dispatcher 	= None # type: ignore

def _setupHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `DMMessage`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(DMMessage, lambda msg: msg.chat.type == "private")


async def DMMessage(msg: MessageType) -> None:
	await msg.answer(f"<b>Привет!</b> 🙋‍♀️\n\nЭтот бот не делает ничего в личных сообщениях, этот бот является частью основного бота, {(await TGBot.get_me()).mention}.")

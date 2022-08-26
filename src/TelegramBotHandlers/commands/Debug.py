# coding: utf-8

"""Обработчик для команды `Debug`."""

import asyncio
from typing import TYPE_CHECKING

import aiogram
from aiogram import Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger

if TYPE_CHECKING:
	from TelegramBot import Telehooper

Bot: 	"Telehooper" 	= None # type: ignore
TGBot:	aiogram.Bot = None # type: ignore
DP: 	Dispatcher 	= None # type: ignore


def _setupCHandler(bot: "Telehooper") -> None:
	"""
	Инициализирует команду `Debug`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(Debug, commands=["Debug"])


async def Debug(msg: MessageType) -> None:
	await asyncio.sleep(5)
	await (await msg.answer("test")).delete()

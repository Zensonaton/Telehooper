# coding: utf-8

"""Обработчик для команды `Debug`."""

import asyncio

from aiogram import Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger
from TelegramBot import Telehooper

TELEHOOPER:	Telehooper = None # type: ignore
DP: 		Dispatcher = None # type: ignore


def _setupHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global TELEHOOPER, DP

	TELEHOOPER = bot
	DP = TELEHOOPER.DP

	DP.register_message_handler(Debug, commands=["Debug"])


async def Debug(msg: MessageType) -> None:
	await asyncio.sleep(5)
	await (await msg.answer("test")).delete()

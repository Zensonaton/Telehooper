# coding: utf-8

"""Обработчик для команды `This`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from Consts import CommandThrottleNames as CThrottle

from Exceptions import CommandAllowedOnlyInBotDialogue, CommandAllowedOnlyInGroup

from TelegramBot import Telehooper
from MiddlewareAPI import TelehooperUser

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper):
	"""
	Инициализирует команду `This`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(This, commands=["this", "thischat"])


async def This(msg: MessageType):
	if msg.chat.type == "private":
		raise CommandAllowedOnlyInGroup()

	await DP.throttle(CThrottle.THIS_DIALOGUE, rate=2, user_id=msg.from_user.id) 
	user = await Bot.getBotUser(msg.from_user.id)

	if msg.chat.type == "group":
		await ThisGroup(msg, user)
	else:
		# Другая проверка на группу.
		await ThisDialogue(msg, user)

async def ThisGroup(msg: MessageType, user: TelehooperUser):
	"""
	Вызывается в группах.
	"""

	await msg.answer("Группа!")

async def ThisDialogue(msg: MessageType, user: TelehooperUser):
	"""
	Вызывается в диалогах.
	"""

	await msg.answer("Диалог!")

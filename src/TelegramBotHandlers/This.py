# coding: utf-8

"""Обработчик для команды `This`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from aiogram.types import Message as MessageType
from Consts import CommandThrottleNames as CThrottle
from Consts import InlineButtonCallbacks as CButton
from Exceptions import (CommandAllowedOnlyInBotDialogue,
                        CommandAllowedOnlyInGroup)
from MiddlewareAPI import TelehooperUser
from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `This`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(This, commands=["this", "thischat"])
	DP.register_callback_query_handler(ThisGroupCallbackHandler, lambda query: query.data == CButton.THIS_COMMAND)


async def This(msg: MessageType):
	if msg.chat.type == "private":
		raise CommandAllowedOnlyInGroup()

	await DP.throttle(CThrottle.THIS_DIALOGUE, rate=2, user_id=msg.from_user.id)

	user = await Bot.getBotUser(msg.from_user.id)
	dialogue = await user.getDialogueGroupByTelegramGroup(msg.chat.id)

	if dialogue:
		await ThisDialogue(msg, user) # TODO: Сообщения.
		return

	# Если в группе:
	await ThisGroup(msg, user)


async def ThisGroup(msg: MessageType, user: TelehooperUser) -> None:
	"""
	Вызывается в группах.
	"""

	await ThisGroupMessage(msg)

async def ThisGroupMessage(msg: MessageType, edit_message_instead: bool = False):
	_text = "ℹ️ Данная Telegram-группа <b>не является диалогом</b> сервиса.\n\n⚙️ Telegram-группу можно преобразовать в диалог, нажав на кнопку ниже:"

	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton(text="♻️ Преобразовать", callback_data=CButton.BACK_TO_GROUP_CONVERTER)
	)

	if edit_message_instead:
		await msg.edit_text(_text, reply_markup=keyboard)
		return

	await msg.answer(_text, reply_markup=keyboard)

async def ThisGroupCallbackHandler(query: CallbackQuery):
	await ThisGroupMessage(query.message, True)

async def ThisDialogue(msg: MessageType, user: TelehooperUser) -> None:
	"""
	Вызывается в диалогах.
	"""

	await msg.answer("Диалог!")

# coding: utf-8

"""Обработчик для команды `RegularMessageHandlers`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from MiddlewareAPI import TelehooperUser
from TelegramBot import DialogueGroup, Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `RegularMessageHandlers`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(RegularMessageHandlers, shouldBeHandled)
	DP.register_edited_message_handler(RegularMessageEditHandler, shouldBeHandled)

async def shouldBeHandled(msg: MessageType):
	"""
	Проверка на то, нужно ли обрабатывать событие сообщения.
	"""

	# Получаем объект пользователя:
	user = await Bot.getBotUser(msg.from_user.id)

	# Узнаём, диалог ли это:
	dialogue = await user.getDialogueGroupByTelegramGroup(msg.chat.id)
	if not dialogue:
		return False

	# Если ок:
	msg._user = user # type: ignore
	msg._dialogue = dialogue # type: ignore
	return True

async def RegularMessageHandlers(msg: MessageType):
	dialogue: DialogueGroup = msg._dialogue # type: ignore
	user: TelehooperUser = msg._user # type: ignore

	reply_message_id = None
	if msg.reply_to_message:
		reply_message_id = user.vkMAPI.getMessageIDByTelegramMID(msg.reply_to_message.message_id)

	# Отправляем сообщение в ВК:
	user.vkMAPI.saveMessageID(msg.message_id, await user.vkMAPI.sendMessageOut(msg.text, dialogue.serviceDialogueID, reply_message_id), msg.chat.id, dialogue.serviceDialogueID)

async def RegularMessageEditHandler(msg: MessageType):
	dialogue: DialogueGroup = msg._dialogue # type: ignore
	user: TelehooperUser = msg._user # type: ignore

	# Редактируем сообщение в ВК.
	# Получаем ID сообщения в ВК через ID сообщения Telegram:
	messageID = user.vkMAPI.getMessageIDByTelegramMID(msg.message_id)
	if messageID:
		await user.vkMAPI.editMessageOut(msg.text, dialogue.serviceDialogueID, messageID)

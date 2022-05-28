# coding: utf-8

"""Обработчик для команды `RegularMessageHandlers`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from TelegramBot import Telehooper

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

	DP.register_message_handler(RegularMessageHandlers)
	DP.register_edited_message_handler(RegularMessageEditHandler)


async def RegularMessageHandlers(msg: MessageType):
	# Получаем объект пользователя:
	user = await Bot.getBotUser(msg.from_user.id)

	# Узнаём, диалог ли это:
	dialogue = await user.getDialogueGroupByTelegramGroup(msg.chat.id)
	if not dialogue:
		return False

	# Отправляем сообщение в ВК:
	user.vkMAPI.saveMessageID(msg.message_id, await user.vkMAPI.sendMessageOut(msg.text, dialogue.serviceDialogueID))

async def RegularMessageEditHandler(msg: MessageType):
	# Получаем объект пользователя:
	user = await Bot.getBotUser(msg.from_user.id)

	# Узнаём, диалог ли это:
	dialogue = await user.getDialogueGroupByTelegramGroup(msg.chat.id)
	if not dialogue:
		return False

	# Редактируем сообщение в ВК.
	# Получаем ID сообщения в ВК через ID сообщения Telegram:
	messageID = user.vkMAPI.getMessageIDByTelegramMID(msg.message_id)
	if messageID:
		await user.vkMAPI.editMessageOut(msg.text, dialogue.serviceDialogueID, messageID)

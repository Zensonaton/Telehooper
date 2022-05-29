# coding: utf-8

"""Обработчик для команды `RegularMessageHandlers`."""

from io import BytesIO
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from MiddlewareAPI import TelehooperUser
from TelegramBot import DialogueGroup, Telehooper
import Utils

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

	# "text", "audio", "document", "photo", "sticker", "video", "video_note", "voice", "location", "contact", "new_chat_members", "left_chat_member", "new_chat_title", "new_chat_photo", "delete_chat_photo", "group_chat_created", "supergroup_chat_created", "channel_chat_created", "migrate_to_chat_id", "migrate_from_chat_id", "pinned_message",

	DP.register_message_handler(RegularMessageHandlers, shouldBeHandled, content_types=["text", "photo", "audio", "voice", "document", "sticker", "video", "video_note"])
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

	# Получаем сообщение из ДБ:
	reply_message_id = None
	if msg.reply_to_message:
		reply_message_id = user.vkMAPI.getMessageIDByTelegramMID(msg.reply_to_message.message_id)
		if reply_message_id:
			reply_message_id = reply_message_id[1]

	# Получаем вложение как File:
	attachedFile = None
	if msg.photo:
		attachedFile = await Utils.File(await msg.photo[-1].download(destination_file=BytesIO())).parse()

	# Отправляем сообщение в ВК:
	user.vkMAPI.saveMessageID(
		msg.message_id, await user.vkMAPI.sendMessageOut(msg.text, dialogue.serviceDialogueID, reply_message_id, attachedFile), msg.chat.id, dialogue.serviceDialogueID
	)

async def RegularMessageEditHandler(msg: MessageType):
	dialogue: DialogueGroup = msg._dialogue # type: ignore
	user: TelehooperUser = msg._user # type: ignore

	# Редактируем сообщение в ВК.
	# Получаем ID сообщения в ВК через ID сообщения Telegram:
	messageID = user.vkMAPI.getMessageIDByTelegramMID(msg.message_id)
	if messageID:
		messageID = messageID[1]

	if messageID:
		await user.vkMAPI.editMessageOut(msg.text, dialogue.serviceDialogueID, messageID)

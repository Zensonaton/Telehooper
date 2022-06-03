# coding: utf-8

"""Обработчик для команды `RegularMessageHandlers`."""

import asyncio
from io import BytesIO
import io
import logging
from typing import List

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from MiddlewareAPI import TelehooperUser
from TelegramBot import DialogueGroup, Telehooper
import Utils

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)



# TODO: Перенести этот Handler в папку ServiceMAPIs.


MEDIA_GROUPS = {}

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

	# Проверяем, подключён ли у него ВК:
	if not user.isVKConnected:
		return False

	# Узнаём, диалог ли это:
	dialogue = await user.getDialogueGroupByTelegramGroup(msg.chat.id)
	if not dialogue:
		return False

	# Если ок:
	msg._user = user # type: ignore
	msg._dialogue = dialogue # type: ignore
	return True

async def checkMediaGroup(media_group_id: str, sleep: float = 0.5) -> List[Utils.File]:
	"""
	Ждёт некоторое время, и после, возвращаем список всех файлов в медиа-группе.
	"""

	# Сначала, спим некоторое время, что бы все сообщения из медиа группы пришли:
	await asyncio.sleep(sleep)

	# После, у нас должен быть полный список всех файлов в медиа группе:
	MEDIA = MEDIA_GROUPS.get(media_group_id, []).copy()

	# Загружаем все файлы с серверов Telegram, и создаем Utils.File объект:
	for index, media in enumerate(MEDIA):
		MEDIA[index] = await Utils.File(await media.download(destination_file=BytesIO())).parse()

	# Удаляем старый список медиа:
	MEDIA_GROUPS.pop(media_group_id)

	# Возвращаем полученный список файлов типа Utils.File:
	return MEDIA

async def RegularMessageHandlers(msg: MessageType):
	dialogue: DialogueGroup = msg._dialogue # type: ignore
	user: TelehooperUser = msg._user # type: ignore

	# Получаем сообщение из ДБ:
	reply_message_id = None
	if msg.reply_to_message:
		reply_message_id = user.vkMAPI.getMessageIDByTelegramMID(msg.reply_to_message.message_id)
		if reply_message_id:
			reply_message_id = reply_message_id.serviceMID

	# Получаем вложение как File:
	attachments: List[Utils.File] = []
	shouldSendMessage: bool = True
	if msg.photo:
		# Если мы получили группу фоток:
		if msg.media_group_id:
			# Как оказалось, в Telegram группа фото отправляется в виде нескольких
			# сообщений, и единственное, что их связывает - значение msg.media_group_id.
			# Нет даже метода узнать, сколько фото в такой группе находится.
			#
			# Единственное решение, что пришло ко мне в голову - запускать "таймер",
			# и по его истечению смотреть всё, что было добавлено в массив.

			if msg.media_group_id not in MEDIA_GROUPS:
				MEDIA_GROUPS[msg.media_group_id] = [msg.photo[-1]]
				# Создаём таймер:
				attachments.extend(await checkMediaGroup(msg.media_group_id))
			else:
				shouldSendMessage = False

				MEDIA_GROUPS[msg.media_group_id].append(msg.photo[-1])
		else:
			attachments.append(await Utils.File(await msg.photo[-1].download(destination_file=BytesIO())).parse())
	elif msg.sticker:
		attachments.append(
			Utils.File(await msg.sticker.download(destination_file=io.BytesIO()), file_type="sticker")
		)
	elif msg.voice:
		attachments.append(
			Utils.File(await msg.voice.download(destination_file=io.BytesIO()), file_type="voice")
		)

	# Отправляем сообщение в ВК:
	if shouldSendMessage:
		user.vkMAPI.saveMessageID(
			msg.message_id,
			await user.vkMAPI.sendMessageOut(
				msg.text
				or msg.caption,
				dialogue.serviceDialogueID,
				reply_message_id,
				attachments
			),
			msg.chat.id,
			dialogue.serviceDialogueID,
			True
		)

async def RegularMessageEditHandler(msg: MessageType):
	dialogue: DialogueGroup = msg._dialogue # type: ignore
	user: TelehooperUser = msg._user # type: ignore

	# Редактируем сообщение в ВК.
	# Получаем ID сообщения в ВК через ID сообщения Telegram:
	messageID = user.vkMAPI.getMessageIDByTelegramMID(msg.message_id)
	if messageID:
		messageID = messageID.serviceMID

	if messageID:
		await user.vkMAPI.editMessageOut(msg.text, dialogue.serviceDialogueID, messageID)

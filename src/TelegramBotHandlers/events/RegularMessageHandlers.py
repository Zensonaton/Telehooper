# coding: utf-8

"""Обработчик для команды `RegularMessageHandlers`."""

import asyncio
import io
from io import BytesIO
from typing import TYPE_CHECKING, Dict, List, cast

import Utils
from aiogram import Dispatcher
from aiogram.types import Message as MessageType, PhotoSize, InlineKeyboardMarkup
from loguru import logger
from ServiceAPIs.VK import VKTelehooperAPI
from TelegramBot import DialogueGroup, Telehooper
import hashlib

if TYPE_CHECKING:
	from TelegramBot import TelehooperUser

TELEHOOPER:	Telehooper = None # type: ignore
DP: 		Dispatcher = None # type: ignore

MEDIA_GROUPS: Dict[str, List[PhotoSize]] = {}


def _setupHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global TELEHOOPER, DP

	TELEHOOPER = bot
	DP = TELEHOOPER.DP

	DP.register_message_handler(RegularMessageHandlers, shouldBeHandled, content_types=["text", "photo", "audio", "voice", "document", "sticker", "video", "video_note"])
	DP.register_edited_message_handler(RegularMessageEditHandler, shouldBeHandled)

async def shouldBeHandled(msg: MessageType):
	"""
	Проверка на то, нужно ли обрабатывать событие сообщения.
	"""

	# Получаем объект пользователя:
	user = await TELEHOOPER.getBotUser(msg.from_user.id)

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
	MEDIA: List[PhotoSize] = MEDIA_GROUPS.get(media_group_id, []).copy()
	NEW_MEDIA: List[Utils.File] = []

	# Загружаем все файлы с серверов Telegram, и создаем Utils.File объект:
	for media in MEDIA:
		downloaded = BytesIO()
		downloaded = (await media.download(destination_file=downloaded)).read()

		NEW_MEDIA.append(
			await Utils.File(
				downloaded,
				file_type="photo",
				uid=media.file_unique_id
			).parse()
		)

	# Удаляем старый список медиа:
	MEDIA_GROUPS.pop(media_group_id)

	# Возвращаем полученный список файлов типа Utils.File:
	return NEW_MEDIA

async def RegularMessageHandlers(msg: MessageType):
	dialogue: DialogueGroup = msg._dialogue # type: ignore
	user: TelehooperUser = msg._user # type: ignore
	TELEHOOPER.vkAPI = cast(VKTelehooperAPI, TELEHOOPER.vkAPI)

	# Получаем сообщение из ДБ:
	reply_message_id = None
	if msg.reply_to_message:
		reply_message_id = TELEHOOPER.vkAPI.getMessageDataByTelegramMID(user, msg.reply_to_message.message_id)
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
			await TELEHOOPER.vkAPI.startDialogueActivity(user, dialogue.serviceDialogueID, "photo")

			downloaded: BytesIO = BytesIO()
			downloaded = await msg.photo[-1].download(destination_file=downloaded)
			bytes = downloaded.read()

			attachments.append(
				await Utils.File(
					bytes,
					file_type="photo",
					uid=msg.photo[-1].file_unique_id
				).parse()
			)
	elif msg.sticker:
		if msg.sticker.is_animated or msg.sticker.is_video:
			await msg.reply("⚠️ Данный бот не поддерживает <b>анимированные стикеры</b>.\n\nДанное сообщение не будет отправлено.")
			
			return

		await TELEHOOPER.vkAPI.startDialogueActivity(user, dialogue.serviceDialogueID, "photo")

		attachments.append(
			Utils.File(
				await msg.sticker.download(destination_file=io.BytesIO()),
				file_type="sticker",
				uid=msg.sticker.file_unique_id
			)
		)
	elif msg.voice:
		await TELEHOOPER.vkAPI.startDialogueActivity(user, dialogue.serviceDialogueID, "audiomessage")

		attachments.append(
			Utils.File(
				await msg.voice.download(destination_file=io.BytesIO()), 
				file_type="voice",
				uid=msg.voice.file_unique_id
			)
		)
	elif msg.video:
		await TELEHOOPER.vkAPI.startDialogueActivity(user, dialogue.serviceDialogueID, "video")

		attachments.append(
			Utils.File(
				await msg.video.download(destination_file=io.BytesIO()),
				file_type="video",
				uid=msg.video.file_unique_id
			)
		)
	elif msg.document:
		attachments.append(
			Utils.File(
				await msg.document.download(destination_file=io.BytesIO()),
				file_type="file",
				uid=msg.document.file_unique_id,
				filename=msg.document.file_name
			)
		)
	else:
		pass

	if not shouldSendMessage:
		return

	# Удаляем предыдущую клавиатуру:
	TELEHOOPER.vkAPI = cast(VKTelehooperAPI, TELEHOOPER.vkAPI)
	latest = TELEHOOPER.vkAPI.getLatestMessageID(
		user,
		dialogue.group.id
	)
	if latest:
		try:
			await TELEHOOPER.TGBot.edit_message_reply_markup(dialogue.group.id, latest.telegram_message_id, reply_markup=InlineKeyboardMarkup())
		except:
			pass

	# Отправляем сообщение в ВК, сохраняя его в базе:
	TELEHOOPER.vkAPI.saveMessageID(
		user,
		msg.message_id,
		await TELEHOOPER.vkAPI.sendMessage(
			user,
			msg.text
			or msg.caption,
			dialogue.serviceDialogueID,
			reply_message_id,
			attachments,
			start_chat_activities=True
		),
		msg.chat.id,
		dialogue.serviceDialogueID,
		True
	)

async def RegularMessageEditHandler(msg: MessageType):
	dialogue: DialogueGroup = msg._dialogue # type: ignore
	user: TelehooperUser = msg._user # type: ignore
	TELEHOOPER.vkAPI = cast(VKTelehooperAPI, TELEHOOPER.vkAPI)

	# Получаем ID сообщения в ВК через ID сообщения Telegram,
	# что бы его отредактировать в ВК.
	messageID = TELEHOOPER.vkAPI.getMessageDataByTelegramMID(user, msg.message_id)

	if not messageID:
		return

	await TELEHOOPER.vkAPI.editMessage(user, msg.text, dialogue.serviceDialogueID, messageID.serviceMID)

# coding: utf-8

"""Обработчик для команды `MarkAsRead`."""

from typing import cast
from aiogram import Dispatcher
from aiogram.types import Message as MessageType, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
from ServiceAPIs.VK import VKTelehooperAPI
from TelegramBot import Telehooper, TelehooperUser
from Consts import InlineButtonCallbacks as CButtons

TELEHOOPER: Telehooper = None # type: ignore
DP: 		Dispatcher = None # type: ignore


def _setupHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global TELEHOOPER, DP

	TELEHOOPER = bot
	DP = TELEHOOPER.DP

	DP.register_message_handler(MarkAsRead, commands=["markasread", "read", "r"])
	DP.register_callback_query_handler(MarkAsReadCallback, lambda query: query.data == CButtons.CommandCallers.MARK_AS_READ)

async def MarkAsRead(msg: MessageType) -> None:	
	# Получаем объект пользователя:
	user = await TELEHOOPER.getBotUser(msg.from_user.id)

	# Проверяем, подключён ли у него ВК:
	if not user.isVKConnected:
		return

	# Прочитываем сообщение:
	await ReadMessage(user, msg.chat.id)

async def MarkAsReadCallback(query: CallbackQuery):
	# Получаем объект пользователя:
	user = await TELEHOOPER.getBotUser(query.from_user.id)

	# Проверяем, подключён ли у него ВК:
	if not user.isVKConnected:
		return

	# Прочитываем сообщение:
	await ReadMessage(user, query.message.chat.id)

	# Прячем кнопку:
	await query.message.edit_reply_markup(InlineKeyboardMarkup())

async def ReadMessage(user: TelehooperUser, chat_id: int):
	TELEHOOPER.vkAPI = cast(VKTelehooperAPI, TELEHOOPER.vkAPI)

	# Узнаём, диалог ли это:
	dialogue = await user.getDialogueGroupByTelegramGroup(chat_id)
	if not dialogue:
		return

	# Последнее сообщение:
	latest = TELEHOOPER.vkAPI.getLatestMessageID(
		user,
		chat_id
	)
	if not latest:
		return

	# Отмечаем сообщение как прочитанное:
	await TELEHOOPER.vkAPI.markAsRead(
		user, 
		dialogue.serviceDialogueID,
		latest.service_message_id
	)

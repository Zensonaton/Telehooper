# coding: utf-8

"""Handler для Callback'а."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery
from aiogram.types import Message as MessageType
from Consts import InlineButtonCallbacks as CButton
from loguru import logger

if TYPE_CHECKING:
	from TelegramBot import Telehooper

TelehooperBot: 	Telehooper 	= None # type: ignore
TGBot: 			Bot 		= None # type: ignore
DP: 			Dispatcher 	= None # type: ignore


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_callback_query_handler(CancelDeleteCurMessageCallbackHandler, lambda query: query.data in [CButton.CancelAction.CANCEL_EDIT_MESSAGE, CButton.CancelAction.CANCEL_DELETE_MESSAGE, CButton.CancelAction.CANCEL_HIDE_BUTTONS])
	DP.register_callback_query_handler(DoNothingCallback, lambda query: query.data == CButton.DO_NOTHING)

async def CancelDeleteCurMessageCallbackHandler(query: CallbackQuery):
	"""
	Редактируем сообщение.
	"""

	if query.data == CButton.CancelAction.CANCEL_DELETE_MESSAGE:
		await query.message.delete()
	elif query.data == CButton.CancelAction.CANCEL_EDIT_MESSAGE:
		await query.message.edit_text("<i>Действие было отменено.</i>")
	else:
		await query.message.edit_text(query.message.html_text)

	return await query.answer()

async def DoNothingCallback(query: CallbackQuery):
	"""
	Ничего вообще не делаем.
	"""

	return await query.answer()

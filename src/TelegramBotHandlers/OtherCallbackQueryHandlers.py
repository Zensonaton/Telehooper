# coding: utf-8

"""Handler для Callback'а."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery
from aiogram.types import Message as MessageType
from Consts import InlineButtonCallbacks as CButton

if TYPE_CHECKING:
	from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_callback_query_handler(CancelDeleteCurMessageCallbackHandler, lambda query: query.data in [CButton.CANCEL_DELETE_CUR_MESSAGE, CButton.CANCEL_EDIT_CUR_MESSAGE])

async def CancelDeleteCurMessageCallbackHandler(query: CallbackQuery):
	if query.data == CButton.CANCEL_DELETE_CUR_MESSAGE:
		await query.message.delete()
	else:
		await query.message.edit_text("<i>Действие было отменено.</i>")

	return await query.answer()

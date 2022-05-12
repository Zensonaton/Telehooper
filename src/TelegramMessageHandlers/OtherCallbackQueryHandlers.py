# coding: utf-8

"""Handler для Callback'а."""

from aiogram.types import Message as MessageType, CallbackQuery
from aiogram import Dispatcher, Bot
from Consts import InlineButtonCallbacks as CButton
import logging

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует Handler.
	"""

	global BOT

	BOT = bot
	dp.register_callback_query_handler(CancelDeleteCurMessageCallbackHandler, lambda query: query.data in [CButton.CANCEL_DELETE_CUR_MESSAGE, CButton.CANCEL_EDIT_CUR_MESSAGE])

async def CancelDeleteCurMessageCallbackHandler(query: CallbackQuery):
	if query.data == CButton.CANCEL_DELETE_CUR_MESSAGE:
		await query.message.delete()
	else:
		await query.message.edit_text("<i>Действие было отменено.</i>")

	return await query.answer()

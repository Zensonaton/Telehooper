# coding: utf-8

from aiogram import Router
from aiogram.filters import Text
from aiogram.types import CallbackQuery


router = Router()

@router.callback_query(Text("do-nothing"))
async def do_nothing_inline_handler(query: CallbackQuery) -> None:
	"""
	Inline Callback Handler для `do-nothing`.

	Делает абсолютно ничего, кроме вызова `query.answer()`, что бы спрятать "часики" в клиенте Telegram.
	"""

	await query.answer()

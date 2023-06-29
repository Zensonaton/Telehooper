# coding: utf-8

from aiogram import Router, types
from aiogram.filters import Text


router = Router()

@router.callback_query(Text("do-nothing"))
async def do_nothing_inline_handler(query: types.CallbackQuery) -> None:
	"""
	Inline Callback Handler для `do-nothing`.

	Делает абсолютно ничего, кроме вызова `query.answer()`, что бы спрятать "часики" в клиенте Telegram.
	"""

	await query.answer()

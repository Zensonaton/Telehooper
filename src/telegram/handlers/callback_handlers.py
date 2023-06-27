# coding: utf-8

from typing import cast
from aiogram import Bot as BotT
from aiogram import Router as RouterT
from aiogram import types
from aiogram.filters import Command, CommandObject, Text
from aiogram.utils.keyboard import InlineKeyboardBuilder

import utils
from consts import FAQ_INFO


Bot: BotT = None # type: ignore
Router = RouterT()

def init(bot: BotT) -> RouterT:
	"""
	Загружает все Handler'ы из этого модуля.
	"""

	global Bot


	Bot = bot

	return Router

@Router.callback_query(Text(startswith="do-nothing"))
async def do_nothing_handler(query: types.CallbackQuery) -> None:
	"""
	Handler для Inline-команды "do nothing".
	"""

	await query.answer()

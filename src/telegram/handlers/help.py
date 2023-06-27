# coding: utf-8

from typing import cast

from aiogram import Bot as BotT
from aiogram import Router as RouterT
from aiogram import types
from aiogram.filters import Command, CommandObject, Text
from aiogram.utils.keyboard import InlineKeyboardBuilder

import utils
from consts import FAQ_INFO, CommandButtons


Bot: BotT = None # type: ignore
Router = RouterT()

def init(bot: BotT) -> RouterT:
	"""
	Загружает все Handler'ы из этого модуля.
	"""

	global Bot


	Bot = bot

	return Router

async def help_message(msg: types.Message, edit_message: bool = False, selected: int = 0) -> None:
	"""
	Сообщение для команды /help.
	"""

	selected_key = list(FAQ_INFO.keys())[selected]
	selected_text = FAQ_INFO[selected_key]

	builder = InlineKeyboardBuilder()

	for index, key in enumerate(FAQ_INFO.keys()):
		is_current = key == selected_key

		builder.add(
			types.InlineKeyboardButton(
				text=f"👉 {key} 👈" if is_current else key,
				callback_data="do-nothing" if is_current else f"faq-page {index}"
			)
		)
	builder.adjust(1)

	if edit_message:
		await msg.edit_text(
			selected_text,
			reply_markup=builder.as_markup(resize_keyboard=True),
			disable_web_page_preview=True
		)
	else:
		await msg.answer(
			selected_text,
			reply_markup=builder.as_markup(resize_keyboard=True),
			disable_web_page_preview=True
		)

@Router.message(Command("help", "info", "faq"))
@Router.message(Text(CommandButtons.HELP))
async def help_handler(msg: types.Message, command: CommandObject | None = None) -> None:
	"""
	Handler для команды /help.
	"""

	selected = 0
	if command and command.args:
		args = command.args.split()

		if args[0].isdigit():
			selected = utils.clamp(
				int(args[0]) - 1,
				0,
				len(FAQ_INFO) - 1
			)

	await help_message(
		msg,
		selected=cast(int, selected)
	)

@Router.callback_query(Text(startswith="faq-page"))
async def help_inline_handler(query: types.CallbackQuery) -> None:
	"""
	Handler для Inline-команды /help.
	"""

	page = utils.clamp(
		int((query.data or "").split()[1]),
		0,
		len(FAQ_INFO) - 1
	)

	await help_message(
		cast(types.Message, query.message),
		edit_message=True,
		selected=int(page)
	)

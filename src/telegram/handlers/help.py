# coding: utf-8

from typing import cast

from aiogram import Router
from aiogram.filters import Command, CommandObject, Text
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

import utils
from api import TelehooperAPI
from consts import FAQ_INFO, CommandButtons


router = Router()

async def help_command_message(msg: Message, edit_message: bool = False, selected: int = 0) -> None:
	"""
	Сообщение для команды `/help`.
	"""

	selected_key = list(FAQ_INFO.keys())[selected]
	selected_text = utils.replace_placeholders(FAQ_INFO[selected_key])

	keyboard_btns = []

	for index, key in enumerate(FAQ_INFO.keys()):
		is_current = key == selected_key

		keyboard_btns.append([
			InlineKeyboardButton(
				text=f"👉 {key} 👈" if is_current else key,
				callback_data="do-nothing" if is_current else f"/help {index}"
			)
		])

	await TelehooperAPI.send_or_edit_message(
		text=selected_text,
		chat_id=msg.chat.id,
		reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_btns),
		disable_web_page_preview=True,
		message_to_edit=msg if edit_message else None
	)

@router.message(Command("help", "info", "faq"))
@router.message(Text(CommandButtons.HELP))
async def help_command_handler(msg: Message, command: CommandObject | None = None) -> None:
	"""
	Handler для команды `/help`.
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

	await help_command_message(
		msg,
		selected=cast(int, selected)
	)

@router.callback_query(Text(startswith="/help"))
async def help_page_inline_handler(query: CallbackQuery) -> None:
	"""
	Inline Callback Handler для команды `/help`.

	Вызывается при выборе страницы.
	"""

	page = utils.clamp(
		int((query.data or "").split()[1]),
		0,
		len(FAQ_INFO) - 1
	)

	await help_command_message(
		cast(Message, query.message),
		edit_message=True,
		selected=int(page)
	)

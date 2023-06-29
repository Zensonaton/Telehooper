# coding: utf-8

from typing import cast

from aiogram import Router, types
from aiogram.filters import Command, Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from consts import CommandButtons
from services.vk.connect_handler import router as VKRouter


router = Router()
router.include_router(VKRouter)

async def connect_command_message(msg: types.Message, edit_message: bool = False) -> None:
	"""
	Сообщение для команды `/connect`.
	"""

	_text = (
		"<b>🌐 Подключение сервиса</b>.\n"
		"\n"
		"В данный момент Вы пытаетесь подключить новый сервис к боту. В данный момент Вам для подключения доступны:\n"
		" • <a href=\"vk.com\">ВКонтакте</a>.\n"
		"\n"
		"ℹ️ Выберите нужный Вам сервис для подключения, а затем следуйте инструкциям, которые будут предоставлены Вам в дальнейшем."
	)

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="ВКонтакте", callback_data="/connect vk")]
	])

	if edit_message:
		await msg.edit_text(
			_text,
			disable_web_page_preview=True,
			reply_markup=keyboard
		)
	else:
		await msg.answer(
			_text,
			disable_web_page_preview=True,
			reply_markup=keyboard
		)

@router.message(Command("connect"))
@router.message(Text(CommandButtons.CONNECT))
async def connect_command_handler(msg: types.Message) -> None:
	"""
	Handler для команды `/connect`.
	"""

	await connect_command_message(msg)

@router.callback_query(Text("/connect"))
async def connect_inline_handler(query: types.CallbackQuery) -> None:
	"""
	Inline Handler для команды `/connect`.

	Вызывается, когда пользователь нажал на кнопку "Назад".
	"""

	await connect_command_message(
		cast(types.Message, query.message),
		edit_message=True
	)

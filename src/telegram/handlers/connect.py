# coding: utf-8

from typing import cast

from aiogram import Bot as BotT
from aiogram import Router as RouterT
from aiogram import types
from aiogram.filters import Command, Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.vk.connect_handler import Router as VKRouter


Bot: BotT = None # type: ignore
Router = RouterT()

def init(bot: BotT) -> RouterT:
	"""
	Загружает все Handler'ы из этого модуля.
	"""

	global Bot


	Bot = bot

	Router.include_router(VKRouter)

	return Router

async def connect_message(msg: types.Message, edit_message: bool = False) -> None:
	"""
	Сообщение для команды /connect.
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
		[
			InlineKeyboardButton(text="ВКонтакте", callback_data="connect vk")
		]
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

@Router.message(Command("connect"))
async def connect_handler(msg: types.Message) -> None:
	"""
	Handler для команды /connect.
	"""

	await connect_message(msg)

@Router.callback_query(Text("connect"))
async def connect_inline_handler(query: types.CallbackQuery) -> None:
	"""
	Inline Handler для команды /connect: Вызывается, когда пользователь нажал на кнопку "назад".
	"""

	await connect_message(
		cast(types.Message, query.message),
		edit_message=True
	)

# coding: utf-8

from aiogram import F, Router
from aiogram.filters import Command, Text
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from api import TelehooperAPI
from consts import CommandButtons
from services.vk.telegram_handlers.connect import router as VKRouter


router = Router()
router.include_router(VKRouter)

async def connect_command_message(msg: Message, edit_message: bool = False) -> None:
	"""
	Сообщение для команды `/connect`.
	"""

	# TODO: Проверить на то, может ли пользователь подключить сервис или нет.
	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="ВКонтакте", callback_data="/connect vk")]
	])

	await TelehooperAPI.send_or_edit_message(
		text = (
			"<b>🌐 Подключение сервиса</b>.\n"
			"\n"
			"В данный момент Вы пытаетесь подключить новый сервис к боту. В данный момент Вам для подключения доступны:\n"
			" • <a href=\"vk.com\">ВКонтакте</a>.\n"
			"\n"
			"ℹ️ Выберите нужный Вам сервис для подключения, а затем следуйте инструкциям, которые будут предоставлены Вам в дальнейшем."
		),
		disable_web_page_preview=True,
		chat_id=msg.chat.id,
		reply_markup=keyboard,
		message_to_edit=msg if edit_message else None
	)

@router.message(Command("connect"))
@router.message(Text(CommandButtons.CONNECT))
async def connect_command_handler(msg: Message) -> None:
	"""
	Handler для команды `/connect`.
	"""

	await TelehooperAPI.restrict_in_debug(msg.from_user)

	await connect_command_message(msg)

@router.callback_query(Text("/connect"), F.message.as_("msg"))
async def connect_inline_handler(query: CallbackQuery, msg: Message) -> None:
	"""
	Inline Handler для команды `/connect`.

	Вызывается, когда пользователь нажал на кнопку "Назад".
	"""

	await connect_command_message(msg, edit_message=True)

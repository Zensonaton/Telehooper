# coding: utf-8

from aiogram import F, Router
from aiogram.filters import Command, Text
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, User)

import utils
from api import TelehooperAPI
from consts import CommandButtons
from services.vk.telegram_handlers.me import router as VKRouter


router = Router()
router.include_router(VKRouter)

async def me_command_message(msg: Message, from_user: User, edit_message: bool = False) -> None:
	"""
	Сообщение для команды `/me`.
	"""

	assert from_user

	user = await TelehooperAPI.get_user(from_user)

	has_any_connections = False
	keyboard = []

	vk_info = "<i>страница не подключена</i>"
	if user.get_vk_connection():
		has_any_connections = True

		id = user.connections["VK"]["ID"]
		full_name = user.connections["VK"]["FullName"]
		domain = user.connections["VK"]["Username"]

		vk_info = f"{full_name} (<a href=\"vk.com/{domain}\">@{domain}</a>, ID {id})"
		keyboard.append(
			InlineKeyboardButton(text="ВКонтакте", callback_data="/me vk")
		)

	await TelehooperAPI.send_or_edit_message(
		text=(
			"<b>👤 Ваш профиль</b>.\n"
			"\n"
			"Базовая информация о Вашем профиле:\n"
			f" • <b>Telegram</b>: {utils.get_telegram_logging_info(msg.from_user)}.\n"
			f" • <b>ВКонтакте</b>: {vk_info}.\n"
			"\n"
			f"ℹ️ {'Вы можете управлять подключёнными сервисами нажимая на кнопки снизу. ' if has_any_connections else ''}Для подключения {'нового' if has_any_connections else 'Вашего первого'} сервиса воспользуйтесь командой /connect."
		),
		disable_web_page_preview=True,
		chat_id=msg.chat.id,
		reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard]),
		message_to_edit=msg if edit_message else None
	)


@router.message(Command("me"))
@router.message(Text(CommandButtons.ME))
async def me_command_handler(msg: Message) -> None:
	"""
	Handler для команды `/me`.
	"""

	assert msg.from_user

	await me_command_message(msg, msg.from_user)

@router.callback_query(Text("/me"), F.message.as_("msg"), F.from_user.as_("user"))
async def me_command_inline_handler(_: CallbackQuery, msg: Message, user: User) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Вызывается при выходе в меню у команды `/me`.
	"""

	await me_command_message(msg, user, edit_message=True)

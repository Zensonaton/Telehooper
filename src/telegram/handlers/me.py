# coding: utf-8

from aiogram import F, Router, types
from aiogram.filters import Command, Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import utils
from api import TelehooperAPI
from consts import CommandButtons
from services.vk.telegram_handlers.me import router as VKRouter


router = Router()
router.include_router(VKRouter)

async def me_command_message(msg: types.Message, from_user: types.User, edit_message: bool = False) -> None:
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

	_text = (
		"<b>👤 Ваш профиль</b>.\n"
		"\n"
		"Базовая информация о Вашем профиле:\n"
		f" • <b>Telegram</b>: {utils.get_telegram_logging_info(msg.from_user)}.\n"
		f" • <b>ВКонтакте</b>: {vk_info}.\n"
		"\n"
		f"ℹ️ {'Вы можете управлять подключёнными сервисами нажимая на кнопки снизу. ' if has_any_connections else ''}Для подключения {'нового' if has_any_connections else 'Вашего первого'} сервиса воспользуйтесь командой /connect."
	)

	if edit_message:
		await msg.edit_text(
			_text,
			disable_web_page_preview=True,
			reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard])
		)
	else:
		await msg.answer(
			_text,
			disable_web_page_preview=True,
			reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard])
		)


@router.message(Command("me"))
@router.message(Text(CommandButtons.ME))
async def me_command_handler(msg: types.Message) -> None:
	"""
	Handler для команды `/me`.
	"""

	assert msg.from_user

	await me_command_message(msg, msg.from_user)

@router.callback_query(Text("/me"), F.message.as_("msg"))
async def me_command_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Вызывается при выходе в меню у команды `/me`.
	"""

	await me_command_message(msg, query.from_user, edit_message=True)

# coding: utf-8

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, User)

import utils
from api import TelehooperAPI
from consts import CommandButtons
from services.vk.telegram_handlers.me import router as VKRouter


router = Router()
router.include_router(VKRouter)

async def me_command_message(msg: Message, bot: Bot, from_user: User, edit_message: bool = False, callback_query: CallbackQuery | None = None) -> None:
	"""
	Сообщение для команды `/me`.
	"""

	assert from_user

	user = await TelehooperAPI.get_user(from_user)

	use_mobile_vk = await user.get_setting("Services.VK.MobileVKURLs")
	has_any_connections = False
	keyboard = []

	vk_info = None
	if user.get_vk_connection():
		has_any_connections = True

		id = user.connections["VK"]["ID"]
		full_name = user.connections["VK"]["FullName"]
		domain = user.connections["VK"]["Username"]

		vk_info = f"{full_name} (<a href=\"{'m.' if use_mobile_vk else ''}vk.com/{domain}\">@{domain}</a>, ID {id})"

	keyboard.append(InlineKeyboardButton(text="ВКонтакте", callback_data="/me vk"))

	connections_info = ""
	if has_any_connections:
		connections_info = (
			"Подключения:\n"
			f" • <b>ВКонтакте</b>: {vk_info or '<i>страница не подключена</i>'}.\n"
			"\n"
		)

	await TelehooperAPI.edit_or_resend_message(
		bot,
		text=(
			"<b>👤 Профиль и сервисы</b>.\n"
			"\n"
			"Информация о Вашем профиле:\n"
			f" • <b>Telegram</b>: {utils.get_telegram_logging_info(from_user)}.\n"
			"\n"
			f"{connections_info}"
			f"ℹ️ {'Для подключения, либо управления сервисами, нажмите на кнопку снизу.' if has_any_connections else 'Выберите нужный сервис снизу, что бы сделать Ваше первое подключение.'}"
		),
		disable_web_page_preview=True,
		chat_id=msg.chat.id,
		reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard]),
		message_to_edit=msg if edit_message else None,
		query=callback_query
	)


@router.message(Command("me", "profile", "connect", "connections"))
@router.message(F.text == CommandButtons.ME)
@router.message(F.text == CommandButtons.CONNECT)
async def me_command_handler(msg: Message, bot: Bot) -> None:
	"""
	Handler для команды `/me`.
	"""

	assert msg.from_user

	await me_command_message(msg, bot, msg.from_user)

@router.callback_query(F.data == "/me", F.message.as_("msg"), F.from_user.as_("user"))
async def me_command_inline_handler(query: CallbackQuery, msg: Message, user: User, bot: Bot) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Вызывается при выходе в меню у команды `/me`.
	"""

	await me_command_message(msg, bot, user, edit_message=True, callback_query=query)

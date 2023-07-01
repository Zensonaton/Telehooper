# coding: utf-8

from aiogram import Router, types
from aiogram.filters import Command, Text
from api import TelehooperAPI

import utils
from consts import CommandButtons


router = Router()

@router.message(Command("me"))
@router.message(Text(CommandButtons.ME))
async def me_command_handler(msg: types.Message) -> None:
	"""
	Handler для команды `/me`.
	"""

	assert msg.from_user

	user = await TelehooperAPI.get_user(msg.from_user)


	vk_info = "<i>страница не подключена</i>"
	if user.get_vk_connection():
		vk_info = f"Имя Фамилия (<a href=\"vk.com\">@username</a>, ID 123456789)" # TODO: Настоящие данные пользователя.

	await msg.answer(
		"<b>👤 Ваш профиль</b>.\n"
		"\n"
		"Базовая информация о Вашем профиле:\n"
		f" • <b>Telegram</b>: {utils.get_telegram_logging_info(msg.from_user)}.\n"
		f" • <b>ВКонтакте</b>: {vk_info}.\n"
		"\n"
		"ℹ️ Вы не понимаете с чего нужно начать? Воспользуйтесь своим личным путеводителем, командой /info.",
		disable_web_page_preview=True
	)

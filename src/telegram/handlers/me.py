# coding: utf-8

from aiogram import Router, types
from aiogram.filters import Command, Text

import utils
from consts import CommandButtons


router = Router()

@router.message(Command("me"))
@router.message(Text(CommandButtons.ME))
async def me_command_handler(msg: types.Message) -> None:
	"""
	Handler для команды `/me`.
	"""

	# TODO: Сделать показ того, что страница ВК подключена.

	await msg.answer(
		"<b>👤 Ваш профиль</b>.\n"
		"\n"
		"Базовая информация о Вашем профиле:\n"
		f" • <b>Telegram</b>: {utils.get_telegram_logging_info(msg.from_user)}.\n"
		f" • <b>ВКонтакте</b>: <i>страница не подключена</i>.\n"
		"\n"
		"ℹ️ Вы не понимаете с чего нужно начать? Воспользуйтесь своим личным путеводителем, командой /info.",
		disable_web_page_preview=True
	)

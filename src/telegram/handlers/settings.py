# coding: utf-8

from aiogram import Router, types
from aiogram.filters import Command, Text

from consts import CommandButtons


router = Router()

@router.message(Command("settings"))
@router.message(Text(CommandButtons.SETTINGS))
async def settings_command_handler(msg: types.Message) -> None:
	"""
	Handler для команды `/settings`.
	"""

	await msg.answer(
		"<b>⚙️ Настройки</b>.\n"
		"\n"
		"В разработке! 👀"
	)

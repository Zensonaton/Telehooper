# coding: utf-8

from aiogram import Bot as BotT
from aiogram import Router as RouterT
from aiogram import types
from aiogram.filters import Command, Text

from consts import CommandButtons


Bot: BotT = None # type: ignore
Router = RouterT()

def init(bot: BotT) -> RouterT:
	"""
	Загружает все Handler'ы из этого модуля.
	"""

	global Bot


	Bot = bot

	return Router

@Router.message(Command("settings"))
@Router.message(Text(CommandButtons.SETTINGS))
async def me_handler(msg: types.Message) -> None:
	"""
	Handler для команды /settings.
	"""

	await msg.answer(
		"<b>⚙️ Настройки</b>.\n"
		"\n"
		"В разработке! 👀"
	)

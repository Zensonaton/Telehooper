# coding: utf-8

from aiogram import Bot as BotT
from aiogram import Router as RouterT
from aiogram import types
from aiogram.filters import Command, Text

import utils
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

@Router.message(Command("me"))
@Router.message(Text(CommandButtons.ME))
async def me_handler(msg: types.Message) -> None:
	"""
	Handler для команды /me.
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

# coding: utf-8

from aiogram import Bot as BotT
from aiogram import Router as RouterT
from aiogram import types
from aiogram.filters import Command


Bot: BotT = None # type: ignore
Router = RouterT()

def init(bot: BotT) -> RouterT:
	"""
	Загружает все Handler'ы из этого модуля.
	"""

	global Bot


	Bot = bot

	Router.message(Command("start"))(start_handler)

	return Router

async def start_handler(msg: types.Message) -> None:
	"""
	Handler для команды /start.
	"""

	await msg.answer(
		"<b>Привет! 🙋</b>\n"
		"\n"
		"Я — бот с <a href=\"https://github.com/Zensonaton/Telehooper\">открытым исходным кодом</a>, позволяющий отправлять и получать сообщения из ВКонтакте напрямую в Telegram. 🤖\n"
		"\n"
		"ℹ️ Для начала работы с ботом воспользуйся командой /info; данная команда будет твоим личным путеводителем в данном боте.",
		disable_web_page_preview=True
	)

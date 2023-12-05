# coding: utf-8

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from consts import GITHUB_SOURCES_URL, CommandButtons


router = Router()

@router.message(Command("start"))
async def start_handler(msg: Message) -> None:
	"""
	Handler для команды `/start`.
	"""

	kbd_buttons = [
		KeyboardButton(text=CommandButtons.CONNECT),
		KeyboardButton(text=CommandButtons.ME),
		KeyboardButton(text=CommandButtons.SETTINGS),
		KeyboardButton(text=CommandButtons.HELP)
	]
	message_text = (
		"<b>Привет! 🙋</b>\n"
		"\n"
		f"Я — бот с <a href=\"{GITHUB_SOURCES_URL}\">открытым исходным кодом</a>, позволяющий отправлять и получать сообщения из ВКонтакте напрямую в Telegram. 🤖\n"
		"\n"
		"Список команд данного бота:\n"
		" • /connect — подключение сервиса к боту.\n"
		" • /me — информация о Вашем профиле.\n"
		" • /settings — изменение настроек.\n"
		" • /info — полезная информация о боте.\n"
		"\n"
		"ℹ️ Вы не понимаете с чего нужно начать? Воспользуйтесь своим личным путеводителем, командой /help."
	)

	if msg.chat.type in ["group", "supergroup"]:
		kbd_buttons.insert(0, KeyboardButton(text=CommandButtons.THIS))

		message_text = (
			"<b>🔍 Список команд в группе</b>.\n"
			"\n"
			"Список команд данного бота:\n"
			" • /this — подключение данной группы к диалогу сервиса.\n"
			" • /connect — подключение сервиса к боту.\n"
			" • /me — информация о Вашем профиле.\n"
			" • /settings — изменение настроек.\n"
			" • /info — полезная информация о боте.\n"
			"\n"
			"ℹ️ Не понимаете что делать дальше? Воспользуйтесь командой /help."
		)

	await msg.answer(message_text,
		disable_web_page_preview=True,
		reply_markup=ReplyKeyboardMarkup(keyboard=[kbd_buttons], resize_keyboard=True, one_time_keyboard=msg.chat.type != "private")
	)

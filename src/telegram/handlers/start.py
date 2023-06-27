# coding: utf-8

from aiogram import Bot as BotT
from aiogram import Router as RouterT
from aiogram import types
from aiogram.filters import Command

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

@Router.message(Command("start"))
async def start_handler(msg: types.Message) -> None:
	"""
	Handler для команды /start.
	"""

	kbd_buttons = [
		types.KeyboardButton(text=CommandButtons.CONNECT),
		types.KeyboardButton(text=CommandButtons.ME),
		types.KeyboardButton(text=CommandButtons.SETTINGS),
		types.KeyboardButton(text=CommandButtons.HELP)
	]
	message_text = (
		"<b>Привет! 🙋</b>\n"
		"\n"
		"Я — бот с <a href=\"https://github.com/Zensonaton/Telehooper\">открытым исходным кодом</a>, позволяющий отправлять и получать сообщения из ВКонтакте напрямую в Telegram. 🤖\n"
		"\n"
		"Список команд данного бота:\n"
		" • /connect — подключение сервиса к боту.\n"
		" • /me — информация о Вашем профиле.\n"
		" • /settings — изменение настроек.\n"
		" • /info — полезная информация о боте.\n"
		"\n"
		"ℹ️ Вы не понимаете с чего нужно начать? Воспользуйтесь своим личным путеводителем, командой /info."
	)

	if msg.chat.type in ["group", "supergroup"]:
		kbd_buttons.append(
			types.KeyboardButton(text=CommandButtons.THIS)
		)
		message_text = (
			"<b>🔍 Список команд в группе</b>.\n"
			"\n"
			"Вы воспользовались командой <code>/start</code> в группе. В группах дополнительно доступны следующие команды:\n"
			" • /this — конвертация текущей группы в сервис-группу.\n"
			"\n"
			"ℹ️ Список команд отличается в зависимости от того, где она была прописана. Не понимаете что делать дальше? Воспользуйтесь командой /info."
		)
	elif msg.chat.type in "channel":
		# TODO: Сделать поддержку каналов.

		raise Exception("Каналы не поддерживаются в данный момент!")

	keyboard = types.ReplyKeyboardMarkup(
		keyboard=[
			kbd_buttons
		],
		resize_keyboard=True,
		is_persistent=msg.chat.type == "private"
	)

	await msg.answer(
		message_text,
		disable_web_page_preview=True,
		reply_markup=keyboard
	)

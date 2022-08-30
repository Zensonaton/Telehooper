# coding: utf-8

"""Обработчик для команды `Settings`."""

from typing import TYPE_CHECKING, cast

import aiogram
from aiogram import Dispatcher
from aiogram.types import Message as MessageType, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Consts import InlineButtonCallbacks as CButtons
from loguru import logger

from Exceptions import CommandAllowedOnlyInPrivateChats
from TelegramBot import TelehooperUser

if TYPE_CHECKING:
	from TelegramBot import Telehooper

TelehooperBot: 	"Telehooper" 	= None # type: ignore
TGBot:	aiogram.Bot 	= None # type: ignore
DP: 	Dispatcher 		= None # type: ignore


def _setupCHandler(bot: "Telehooper") -> None:
	"""
	Инициализирует команду `Settings`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(Settings, commands=["settings", "options", "setting", "option", "s"])
	DP.register_callback_query_handler(SettingsCallbackHandler, lambda query: query.data.startswith(CButtons.CommandActions.GOTO_SETTING))

async def Settings(msg: MessageType) -> None:
	if msg.chat.type != "private":
		raise CommandAllowedOnlyInPrivateChats

	await SettingsMessage(msg)

async def SettingsMessage(msg: MessageType, edit_message_instead: bool = False, force_path: str | None = None, user: TelehooperUser | None = None) -> None:
	if not user:
		user = await TelehooperBot.getBotUser(msg.from_user.id)

	args = msg.get_args()
	if force_path:
		args = force_path

	isGivenPathRight = False
	curObject = None
	isAFile = False
	keyboard = InlineKeyboardMarkup(row_width=2)

	# Пытаемся пропарсить путь, данный пользователем:
	path = []
	pathStr = ""
	if args:
		path = TelehooperBot.settingsHandler.listPath(force_path if force_path else args)

		isGivenPathRight = bool(path)

		# Проверяем, правильный ли дал пользователь путь.
		# Если да, то пытаемся достать объект, связанный с путём.
		if isGivenPathRight:
			path = cast(list[str], path)
			pathStr = ".".join(path)

			curObject = cast(dict, TelehooperBot.settingsHandler.getByPath(pathStr))
			isAFile = curObject["IsAFile"]

	# Сохраняем будущие тексты для отправки:
	_text = ""
	if not isGivenPathRight and args:
		_text = f"<b>Настройки ⚙️</b>\n\nНастройки «<code>{args}</code>» не существует. Пожалуйста, снова воспользуйся командой /settings что бы начать всё сначала.\nЕсли ты получил введённую тобою команду от бота, то, пожалуйста, создай <a href=\"https://github.com/Zensonaton/Telehooper\">Issue на Github проекта</a>."
	elif isAFile:
		# У нас есть валидная настройка, даем пользователю изменить её.

		path = cast(list[str], path)
		curObject = cast(dict, curObject)

		keyboard.add(
			InlineKeyboardButton("🔙 Вернуться назад", callback_data=CButtons.CommandActions.GOTO_SETTING + ".".join(path[:-1])),
			InlineKeyboardButton("🔙 На главную страницу", callback_data=CButtons.CommandActions.GOTO_SETTING)
		)

		keyboard.add(
			InlineKeyboardButton("And she spoke words that will melt in your hands,", callback_data="a"),
		)
		keyboard.add(
			InlineKeyboardButton("And she spoke words of wisdom", callback_data="a"),
		)
		keyboard.add(
			InlineKeyboardButton("ㅤ", callback_data="a"),
		)
		keyboard.add(
			InlineKeyboardButton("To the basement people, to the basement", callback_data="a"),
		)
		keyboard.add(
			InlineKeyboardButton("Many surprises await you", callback_data="a"),
		)

		_text = f"<b>Настройки ⚙️</b>\n\n{TelehooperBot.settingsHandler.renderByPath(path, user)}\n\nℹ️ <b>{curObject['Name']}</b>:\n{curObject['Documentation']}\n\n\nТекущее значение настройки: ✅ Включено (да).\nУправлять значением данной настройки можно через кнопки ниже:"
	elif not isAFile:
		# У нас дана папка, даём пользователю дальше прыгать по папкам:

		path = cast(list[str], path)
		curObject = cast(dict, curObject)

		if path:
			if len(path) > 1:
				keyboard.insert(
					InlineKeyboardButton("🔙 Вернуться назад", callback_data=CButtons.CommandActions.GOTO_SETTING + ".".join(path[:-1]))
				)

			keyboard.insert(
				InlineKeyboardButton("🔙 На главную страницу", callback_data=CButtons.CommandActions.GOTO_SETTING)
			)


		else:
			keyboard.add(
				InlineKeyboardButton("ㅤ", callback_data=CButtons.DO_NOTHING) 
			)

		# Разделим.
		keyboard.row()

		# Добавим все папки и файлы.
		folders = cast(dict, TelehooperBot.settingsHandler.getFolders(pathStr))
		for index, folder in enumerate(folders):
			folderName = folder
			folder = folders[folder]

			keyboard.insert(
				InlineKeyboardButton("📁 " + folder["Name"], callback_data=CButtons.CommandActions.GOTO_SETTING + folder["FullPath"])
			)

		files = cast(dict, TelehooperBot.settingsHandler.getFiles(pathStr))
		for index, file in enumerate(files):
			fileName = file
			file = files[file]

			keyboard.insert(
				InlineKeyboardButton("⚙️ " + file["Name"], callback_data=CButtons.CommandActions.GOTO_SETTING + file["FullPath"])
			)


		_text = f"<b>Настройки ⚙️</b>\n\nДля навигации по этому меню используй <b>кнопки</b> под этим сообщением. Навигайся по разным <b>«разделам»</b> настроек, отмеченных эмодзи 📁, что бы найти <b>индивидуальные настройки</b>, отмеченные эмодзи ⚙️, расположенные внутри этих «разделов».\n\n{TelehooperBot.settingsHandler.renderByPath(path, user)}"
	else:
		logger.error(f"Невозможный кейс в /settings. args=\"{args}\"")
		_text = "Если ты увидел это сообщение, то, пожалуйста, создай <a href=\"https://github.com/Zensonaton/Telehooper\">Issue на Github проекта</a>, поскольку это - баг :)"

	# Отправляем или редактируем сообщение:
	if edit_message_instead:
		await msg.edit_text(_text, reply_markup=keyboard)
	else:
		await msg.answer(_text, reply_markup=keyboard)

async def SettingsCallbackHandler(query: CallbackQuery):
	newPath = query.data.split(CButtons.CommandActions.GOTO_SETTING)[-1]

	await SettingsMessage(
		query.message, 
		True, 
		newPath,
		await TelehooperBot.getBotUser(query.from_user.id)
	)


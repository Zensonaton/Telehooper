# coding: utf-8

# Код для логики Telegram-бота.

import logging
import os

import aiogram

logger = logging.getLogger(__name__)


def initTelegramBot(telegram_bot_token: str, parse_mode: str = aiogram.types.ParseMode.HTML):
	"""
	Инициализирует Telegram-бота.
	"""

	# Инициализируем Telegram-бота:
	Bot = aiogram.Bot(
		token       = telegram_bot_token,
		parse_mode  = parse_mode
	)

	# Создаём Dispatcher:
	DP = aiogram.Dispatcher(Bot)

	# Инициализируем все команды (handler'ы):
	_initHandlers(DP, Bot)

	return Bot, DP

def _initHandlers(dp: aiogram.Dispatcher, bot: aiogram.Bot):
	"""
	Инициализирует все handler'ы бота.
	"""

	from TelegramMessageHandlers import Debug, Setup, Start, VKLogin
	MESSAGE_HANDLERS_IMPORTED = [Start, Debug, Setup, VKLogin]
	MESSAGE_HANDLERS_IMPORTED_FILENAMES = [i.__name__.split(".")[-1] + ".py" for i in MESSAGE_HANDLERS_IMPORTED]

	# Загружаем команды.
	logger.debug(f"Было импортировано {len(MESSAGE_HANDLERS_IMPORTED)} handler'ов, загружаю их...")

	# Предупреждение, если был найден .py файл, но он не был импортирован выше:
	files_found = [i for i in os.listdir("src/TelegramMessageHandlers") if i.endswith(".py") and not i == "__init__.py"]
	files_not_imported = [i for i in files_found if i not in MESSAGE_HANDLERS_IMPORTED_FILENAMES]

	if files_not_imported:
		logger.warning(f"Был обнаружен файл \"{(', '.join(files_not_imported))}\" в папке с handler'ами, и он не был загружен в программу, поскольку импорт не был выполнен в коде файла TelegramBot.py!")

	for index, messageHandler in enumerate(MESSAGE_HANDLERS_IMPORTED):
		messageHandler._setupCHandler(dp, bot)
		logger.debug(f"Инициализирован обработчик команды \"{MESSAGE_HANDLERS_IMPORTED_FILENAMES[index]}\".")
	logger.debug(f"Все handler'ы были загружены успешно!")

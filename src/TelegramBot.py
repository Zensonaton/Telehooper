# coding: utf-8

# Код для логики Telegram-бота.

import logging
import os
from typing import Optional

import aiogram
from aiogram.contrib.fsm_storage.memory import MemoryStorage

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
	DP = aiogram.Dispatcher(Bot, storage=MemoryStorage())

	# Инициализируем все команды (handler'ы):
	_initHandlers(DP, Bot)

	return Bot, DP

def _initHandlers(dp: aiogram.Dispatcher, bot: aiogram.Bot):
	"""
	Инициализирует все handler'ы бота.
	"""

	from TelegramMessageHandlers import Debug, Setup, Start, VKLogin
	importHandlers([Debug, Setup, Start, VKLogin], dp, bot, is_multibot=False)


	dp.errors_handler()(global_error_handler)

def initMultibot(telegram_bot_token: str, mainBot: aiogram.Bot, parse_mode: str = aiogram.types.ParseMode.HTML):
	"""
	Инициализирует Мини-Telegram бота для функции мультибота.
	"""

	# Инициализируем Telegram-бота:
	Bot = aiogram.Bot(
		token       = telegram_bot_token,
		parse_mode  = parse_mode
	)

	# Создаём Dispatcher:
	DP = aiogram.Dispatcher(Bot, storage=MemoryStorage())

	# Инициализируем все команды (handler'ы):
	_initMultibotHandlers(DP, Bot, mainBot)

	return Bot, DP

def _initMultibotHandlers(dp: aiogram.Dispatcher, bot: aiogram.Bot, mainBot: aiogram.Bot):
	"""
	Инициализирует все handler'ы для Мультибота.
	"""

	from MultibotTelegramMessageHandlers import DMMessage, Test
	importHandlers([Test, DMMessage], dp, bot, is_multibot=True, mainBot=mainBot)

	dp.errors_handler()(global_error_handler)

async def global_error_handler(update, exception):
	"""
	Глобальный обработчик ВСЕХ ошибок у бота.
	"""

	if isinstance(exception, aiogram.utils.exceptions.Throttled):
		await update.message.answer("⏳ Превышен лимит количества запросов использования команды. Попробуй позже.")
	else:
		await update.message.answer(f"⚠️ Произошла ошибка: <code>{exception}</code>.\nПопробуй позже.\n\nТак же, ты можешь зарепортить баг в <a href=\"https://github.com/Zensonaton/Telehooper/issues\">Issues</a> проекта.")

		logger.exception(exception)

	return True

def importHandlers(handlers, dp: aiogram.Dispatcher, bot: aiogram.Bot, mainBot: Optional[aiogram.Bot] = None, is_multibot: bool = False):
	"""
	Загружает (импортирует?) все Handler'ы в бота.
	"""

	MESSAGE_HANDLERS_IMPORTED = handlers
	MESSAGE_HANDLERS_IMPORTED_FILENAMES = [i.__name__.split(".")[-1] + ".py" for i in MESSAGE_HANDLERS_IMPORTED]

	# Загружаем команды.
	logger.debug(f"Было импортировано {len(MESSAGE_HANDLERS_IMPORTED)} handler'ов, загружаю их...")

	# Предупреждение, если был найден .py файл, но он не был импортирован выше:
	files_found = [i for i in os.listdir("src/" + ("MultibotTelegramMessageHandlers" if is_multibot else "TelegramMessageHandlers")) if i.endswith(".py") and not i == "__init__.py"]
	files_not_imported = [i for i in files_found if i not in MESSAGE_HANDLERS_IMPORTED_FILENAMES]

	if files_not_imported:
		logger.warning(f"Был обнаружен файл \"{(', '.join(files_not_imported))}\" в папке с handler'ами, и он не был загружен в программу, поскольку импорт не был выполнен в коде файла TelegramBot.py!")

	for index, messageHandler in enumerate(MESSAGE_HANDLERS_IMPORTED):
		if is_multibot:
			messageHandler._setupCHandler(dp, bot, mainBot)
		else:
			messageHandler._setupCHandler(dp, bot)

		logger.debug(f"Инициализирован обработчик команды \"{MESSAGE_HANDLERS_IMPORTED_FILENAMES[index]}\".")

	logger.debug(f"Все handler'ы были загружены успешно!")

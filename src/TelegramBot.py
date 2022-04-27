# coding: utf-8

# Код для логики Telegram-бота.

import aiogram
import logging

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

	from TelegramMessageHandlers import Start, Debug
	MESSAGE_HANDLERS_IMPORTED = [Start, Debug]

	# Загружаем команды.
	logger.debug(f"Было импортировано {len(MESSAGE_HANDLERS_IMPORTED)} handler'ов, загружаю их...")
	for messageHandler in MESSAGE_HANDLERS_IMPORTED:
		messageHandler._setupCHandler(dp, bot)
		logger.debug(f"Инициализирован обработчик команды \"{messageHandler.__name__.split('.')[-1]}\".")
	logger.debug(f"Все handler'ы были загружены успешно!")

# coding: utf-8

# Основной файл бота.

import asyncio
import logging
import logging.handlers
import os

import aiogram
import dotenv

import Consts
import TelegramBot as TGBot
import Utils

# Логирование.
logger = logging.getLogger(__name__)
os.makedirs("Logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)-8s %(asctime)s at %(funcName)s]: %(message)s",
	datefmt="%d.%d.%Y %H:%M:%S",
    handlers=[
        logging.handlers.RotatingFileHandler("Logs/TGBot.log", maxBytes=10485760, backupCount=0),
        logging.StreamHandler()
    ]
)



# Загружаем .env файл.
dotenv.load_dotenv()

# Проверяем на наличие всех необходимых env-переменных:
for envVar in Consts.REQUIREDENVVARS:
	if envVar not in os.environ:
		raise Exception(f"Не найдена важная переменная окружения в файле .env \"{envVar}\". {Consts.REQUIREDENVVARS[envVar]}")

# Сохраняем значения env-переменных:
TELEGRAM_BOT_TOKEN = os.environ["TOKEN"]

# Достаём значения опциональных env-переменных.
SKIP_UPDATES = Utils.parseStrAsBoolean(os.environ.get("SKIP_TELEGRAM_UPDATES", True))

# Создаём Telegram-бота:
Bot, DP = TGBot.initTelegramBot(TELEGRAM_BOT_TOKEN)

async def onBotStart(bot: aiogram.Bot):
	"""
	Функция, запускающаяся ПОСЛЕ запуска Telegram-бота.
	"""

	logger.info("Бот запущен успешно! Hello, world!")

# Запускаем бота.
if __name__ == "__main__":
	logger.info("Запускаю бота...")

	aiogram.utils.executor.start_polling(
		dispatcher=DP,
		on_startup=onBotStart,
		skip_updates=SKIP_UPDATES
	)

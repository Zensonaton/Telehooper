# coding: utf-8

# Основной файл бота.

from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import os

import aiogram
import dotenv
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import Consts
import MiddlewareAPI
import TelegramBot as TGBot
import Utils
from Consts import AccountDisconnectType
from Consts import InlineButtonCallbacks as CButtons
from Consts import MAPIServiceType
from DB import getDefaultCollection

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
HOOPER = TGBot.Telehooper(TELEGRAM_BOT_TOKEN)
HOOPER.initTelegramBot()

# Подключаемся к ДБ:
DB = getDefaultCollection()

async def onBotStart(dp: aiogram.Dispatcher):
	"""
	Функция, запускающаяся ПОСЛЕ запуска Telegram-бота.
	"""

	# TODO: Эта функция кажется некрасивой, стоит переписать её!

	# Производим восстановление всех сессий:
	logger.info("Бот запущен успешно! Пытаюсь авторизовать всех пользователей подключённых сервисов...")

	# Извлекаем из ДБ список всех активных сессий ВК:
	for doc in DB.find({"Services.VK.Auth": True}):
		if doc["Services"]["VK"]["Auth"]:
			logger.debug(f"Обнаружен авторизованный в ВК пользователь с TID {doc['_id']}, авторизовываю...")

			telegramUser = (await HOOPER.TGBot.get_chat_member(doc["_id"], doc["_id"])).user
			vkAccount: MiddlewareAPI.VKAccount
			mAPI: MiddlewareAPI.MiddlewareAPI = None # type: ignore
			try:
				# TODO: ensure_future()

				# Пытаемся авторизоваться. vkAccount более не используется, самое главное - создание Longpoll'а.
				mAPI = MiddlewareAPI.MiddlewareAPI(telegramUser)
				vkAccount = await mAPI.connectVKAccount(doc["Services"]["VK"]["Token"], True, doc["Services"]["VK"]["IsAuthViaPassword"])
			except Exception as error:
				logger.warning(f"Ошибка авторизации пользователя с TID {doc['_id']}: {error}")

				if mAPI is not None:
					await mAPI.processServiceDisconnect(MAPIServiceType.VK, AccountDisconnectType.EXTERNAL)

				# TODO: Заменить этот код:
				keyboard = InlineKeyboardMarkup().add(
					InlineKeyboardButton(text="Снова авторизоваться", callback_data=CButtons.ADD_VK_ACCOUNT),
				)

				await HOOPER.TGBot.send_message(telegramUser.id, "⚠️ После моей перезагрузки я не сумел авторизоваться в твой аккаунт <b>«ВКонтакте»</b>.\nЕсли бот был отключён от ВКонтакте специально, например, путём отключения всех приложений/сессий в настройках безопасности, то волноваться незачем.\n\n⚙️ Ты снова можешь авторизоваться, нажав на кнопку ниже:", reply_markup=keyboard)

	# Авторизуем всех остальных 'миниботов' для функции мультибота:
	helperbots = os.environ.get("HELPER_BOTS", "[]")

	logging.getLogger("aiogram.dispatcher.dispatcher").disabled = True
	try:
		helperbots = json.loads(helperbots)
	except Exception as error:
		logger.warning("У меня не удалось загрузить переменную среды \"HELPER_BOTS\" как JSON-объект: %s", error)
	else:
		logger.info(f"Было обнаружено {len(helperbots)} 'миниботов' в настройках переменных среды, пытаюсь авторизовать их...")
		loop = asyncio.get_event_loop()

		for index, token in enumerate(helperbots):
			try:
				MINIBOT = TGBot.Minibot(HOOPER, token)
				MINIBOT.initTelegramBot()

				loop.create_task(MINIBOT.DP.start_polling(), name=f"Multibot-{index+1}")
				logger.debug(f"Мультибот #{index+1}/{len(helperbots)} был запущен!")
			except Exception as error:
				logger.warning(f"Мультибота #{index+1} не удалось подключить: {error}")
	finally:
		logger.info("Завершил подключение миниботов.")

# Запускаем бота.
if __name__ == "__main__":
	logger.info("Запускаю бота...")

	# Загружаем основного бота:
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	aiogram.utils.executor.start_polling(
		dispatcher=HOOPER.DP,
		on_startup=onBotStart,
		skip_updates=SKIP_UPDATES,
		loop=loop,
	)

# coding: utf-8

# Основной файл бота.

from __future__ import annotations

import asyncio
import json
import os
import sys

import aiogram
import dotenv
from loguru import logger

import Consts
import TelegramBot as TGBot
import Utils
from DB import getDefaultCollection
from ServiceMAPIs.VK_new import VKTelehooperAPI
from Consts import AccountDisconnectType

# Логирование.
os.makedirs("Logs", exist_ok=True)
logger.remove()
logger.add("Logs/TGBot.log", catch=True)
logger.add(sys.stdout, colorize=True, backtrace=True, diagnose=True, catch=True)

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
HOOPER = TGBot.Telehooper(
	TELEGRAM_BOT_TOKEN
)
HOOPER.initTelegramBot()

# Подключаемся к ДБ:
DB = getDefaultCollection()

async def onBotStart(dp: aiogram.Dispatcher) -> None:
	"""
	Функция, запускающаяся ПОСЛЕ запуска Telegram-бота.
	"""

	global DB, HOOPER

	if DB.find_one({"_id": "_global"}) is None:
		DB.update_one({
				"_id": "_global"
			}, {
				"$set": {
					"_id": "_global",
					"TempDownloadImageFileID": None,
					"ServiceDialogues": {
						"VK": []
					}
				}
			},
			upsert=True
		)

	# Производим восстановление всех сессий:
	logger.info("Бот запущен успешно! Пытаюсь авторизовать всех пользователей подключённых сервисов...")

	# Подключаем сервисы как API:
	HOOPER.vkAPI = VKTelehooperAPI(HOOPER)

	# Извлекаем из ДБ список всех активных сессий ВК:
	for doc in DB.find({"Services.VK.Auth": True}):
		if doc["Services"]["VK"]["Auth"]:
			logger.debug(f"Обнаружен авторизованный в ВК пользователь с TID {doc['_id']}, авторизовываю...")

			user: TGBot.TelehooperUser | None = None 
			try:
				# Авторизуемся, и после авторизации обязательно запускаем Polling для получения новых сообщений.

				user = await HOOPER.getBotUser(int(doc["_id"]))
				
				await HOOPER.vkAPI.reconnect(user, doc["Services"]["VK"]["Token"])
			except Exception as error:
				# Что-то пошло не так, и мы не смогли восстановить сессию пользователя.

				logger.error(f"Ошибка авторизации пользователя с TID {doc['_id']}: {error}")

				if user and user:
					await HOOPER.vkAPI.disconnect(user, AccountDisconnectType.ERRORED)

				# TODO: Другое сообщение.
				await HOOPER.TGBot.send_message(int(doc['_id']), "<b>Аккаунт был отключён от Telehooper</b> ⚠️\n\nПосле собственной перезагрузки, я не сумел переподключиться к аккаунту ВКонтакте. Если бот был отключён от ВКонтакте специально, например, путём отключения всех приложений/сессий в настройках безопасности, то волноваться незачем. В ином случае, ты можешь снова переподключить аккаунт, воспользовавшись командою /self.")

	# Авторизуем всех остальных 'миниботов' для функции мультибота:
	helperbots = os.environ.get("HELPER_BOTS", "[]")

	# logging.getLogger("aiogram.dispatcher.dispatcher").disabled = True
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

# TODO: Поддержка супер групп

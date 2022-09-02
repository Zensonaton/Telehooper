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
from Consts import AccountDisconnectType
from DB import getDefaultCollection
from ServiceAPIs.VK import VKTelehooperAPI

# Загружаем .env файл.
dotenv.load_dotenv()

# Логирование.
IS_DEBUG = Utils.parseStrAsBoolean(os.environ.get("DEBUG", "false"))

os.makedirs("Logs", exist_ok=True)
logger.remove()
logger.add("Logs/TGBot.log", catch=True, level="DEBUG" if IS_DEBUG else "INFO")
logger.add(sys.stdout, colorize=True, backtrace=IS_DEBUG, diagnose=IS_DEBUG, catch=True, level="DEBUG" if IS_DEBUG else "INFO")

# Проверяем на наличие всех необходимых env-переменных:
for envVar in Consts.REQUIREDENVVARS:
	if envVar not in os.environ:
		raise Exception(f"Не найдена важная переменная окружения в файле .env \"{envVar}\". {Consts.REQUIREDENVVARS[envVar]}")

# Сохраняем значения env-переменных:
TELEGRAM_BOT_TOKEN = os.environ["TOKEN"]

# Подключаемся к ДБ:
DB = getDefaultCollection()

# Достаём значения опциональных env-переменных.
SKIP_UPDATES = Utils.parseStrAsBoolean(os.environ.get("SKIP_TELEGRAM_UPDATES", True))

# Создаём Telegram-бота:
TELEHOOPER = TGBot.Telehooper(
	TELEGRAM_BOT_TOKEN
)

async def onBotStart(dp: aiogram.Dispatcher) -> None:
	"""
	Функция, запускающаяся ПОСЛЕ запуска Telegram-бота.
	"""

	global DB, TELEHOOPER

	if DB.find_one({"_id": "_global"}) is None:
		DB.update_one({
				"_id": "_global"
			}, {
				"$set": {
					"_id": "_global",
					"TempDownloadImageFileID": None,
					"ServiceDialogues": {
						"VK": []
					},
					"ResourceCache": {
						"VK": []
					}
				}
			},
			upsert=True
		)

	logger.info("Бот запущен успешно!")

	# Производим восстановление всех сессий:
	logger.info("Пытаюсь авторизовать всех пользователей подключённых сервисов...")

	# Подключаем сервисы как API:
	TELEHOOPER.vkAPI = VKTelehooperAPI(TELEHOOPER)

	# Извлекаем из ДБ список всех активных сессий ВК:
	for doc in DB.find({"Services.VK.Auth": True}):
		if doc["Services"]["VK"]["Auth"]:
			logger.debug(f"Обнаружен авторизованный в ВК пользователь с TID {doc['_id']}, авторизовываю...")

			user: TGBot.TelehooperUser | None = None 
			try:
				# Авторизуемся, и после авторизации обязательно запускаем Polling для получения новых сообщений.

				user = await TELEHOOPER.getBotUser(int(doc["_id"]))
				
				await TELEHOOPER.vkAPI.reconnect(user, Utils.decryptWithEnvKey(doc["Services"]["VK"]["Token"]))
			except Exception as error:
				# Что-то пошло не так, и мы не смогли восстановить сессию пользователя.

				logger.error(f"Ошибка авторизации пользователя с TID {doc['_id']}: {error}")

				if user and user:
					await TELEHOOPER.vkAPI.disconnect(user, AccountDisconnectType.ERRORED)

				# TODO: Другое сообщение.
				await TELEHOOPER.TGBot.send_message(int(doc['_id']), "<b>Аккаунт был отключён от Telehooper</b> ⚠️\n\nПосле собственной перезагрузки, я не сумел переподключиться к аккаунту ВКонтакте. Если бот был отключён от ВКонтакте специально, например, путём отключения всех приложений/сессий в настройках безопасности, то волноваться незачем. В ином случае, ты можешь снова переподключить аккаунт, воспользовавшись командою /me.")

	# Авторизуем всех остальных 'миниботов' для функции мультибота:
	helperbots = os.environ.get("HELPER_BOTS", "[]")

	try:
		helperbots = json.loads(helperbots)
	except Exception as error:
		logger.warning("У меня не удалось загрузить переменную среды \"HELPER_BOTS\" как JSON-объект: %s", error)
	else:
		logger.info(f"Было обнаружено {len(helperbots)} 'миниботов' в настройках переменных среды, пытаюсь авторизовать их...")
		loop = asyncio.get_event_loop()

		for index, token in enumerate(helperbots):
			try:
				MINIBOT = TGBot.Minibot(TELEHOOPER, token)
				MINIBOT.initTelegramBot()

				loop.create_task(MINIBOT.DP.start_polling(), name=f"Multibot-{index+1}")
				logger.debug(f"Мультибот #{index+1}/{len(helperbots)} был запущен!")
			except Exception as error:
				logger.warning(f"Мультибота #{index+1} не удалось подключить: {error}")
	finally:
		logger.info("Завершил подключение миниботов.")

# Запускаем бота.
if __name__ == "__main__":
	# Проверяем древо настроек:
	logger.info("Проверяем правильность древа настроек.")
	TELEHOOPER.settingsHandler.testIntegrity()

	logger.info("Запускаю бота.")
	TELEHOOPER.initTelegramBot()

	# Загружаем основного бота:
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	aiogram.utils.executor.start_polling(
		dispatcher=TELEHOOPER.DP,
		on_startup=onBotStart,
		skip_updates=SKIP_UPDATES,
		loop=loop,
	)

# TODO: Поддержка супер групп

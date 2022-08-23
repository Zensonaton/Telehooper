# coding: utf-8

# Код для логики Telegram-бота.

from __future__ import annotations

import datetime
import logging
import os
from typing import List, Optional, Tuple

import aiogram
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import Exceptions
from Consts import MAPIServiceType
from DB import getDefaultCollection
from MiddlewareAPI import TelehooperUser
from TelegramBotHandlers import OtherCallbackQueryHandlers

logger = logging.getLogger(__name__)

class Telehooper:
	"""
	Главный класс бота. Он включает в себя MAPI, Telegram Bot'а и прочее.
	"""

	token: str
	parse_mode: str
	storage: MemoryStorage

	DP: aiogram.Dispatcher
	TGBot: aiogram.Bot

	miniBots: List[Minibot]

	telehooperbotUsers: List[TelehooperUser]
	dialogueGroupsList: List[DialogueGroup]


	def __init__(self, telegram_bot_token: str, telegram_bot_parse_mode = aiogram.types.ParseMode.HTML, storage: Optional[MemoryStorage] = None) -> None: # type: ignore
		self.token = telegram_bot_token
		self.parse_mode = telegram_bot_parse_mode  # type: ignore

		self.miniBots = []

		self.telehooperbotUsers = []
		self.dialogueGroupsList = []

		if storage is None:
			self.storage = MemoryStorage()
		else:
			self.storage = storage


	def initTelegramBot(self) -> Tuple[aiogram.Bot, aiogram.Dispatcher]:
		"""
		Инициализирует Telegram-бота.
		"""

		# Инициализируем Telegram-бота:
		Bot = aiogram.Bot(
			token       = self.token,
			parse_mode  = self.parse_mode
		)

		# Создаём Dispatcher:
		DP = aiogram.Dispatcher(Bot, storage=self.storage)

		# Сохраняем в класс:
		self.DP = DP
		self.TGBot = Bot

		# Инициализируем все команды (handler'ы):
		self.initTelegramBotHandlers()

		return Bot, DP

	def initTelegramBotHandlers(self) -> None:
		"""
		Инициализирует все handler'ы бота.
		"""

		# Импортируем все Handler'ы как модули:
		from TelegramBotHandlers.commands import (
			Debug, Help, Self, Start, This, VKLogin
		)
		from TelegramBotHandlers.events import (
			GroupEvents, RegularMessageHandlers
		)
		from TelegramBotHandlers import (
			OtherCallbackQueryHandlers
		)

		# А теперь добавляем их в бота:
		importHandlers([Start, VKLogin, GroupEvents, OtherCallbackQueryHandlers, This, Self, RegularMessageHandlers, Debug, Help], self, is_multibot=False)

		# Отдельно добавляю Error Handler:
		self.DP.errors_handler()(global_error_handler)

	def addMinibot(self, minibot: Minibot):
		"""
		Добавляет минибота в класс.
		"""

		self.miniBots.append(minibot)

	async def getBotUser(self, user_id: int) -> TelehooperUser:
		"""
		Возвращает пользователя бота. Если его нет в кэше, то он будет создан.
		"""

		# Проверяем, не является ли пользователь ботом:
		if user_id == self.TGBot.id:
			raise Exception("getBotUser() попытался получить бота Telehooper.")


		# Пытаемся найти пользователя:
		for user in self.telehooperbotUsers:
			if user.TGUser.id == user_id:
				return user

		# Пользователь не был найдем, создаём нового и его возвращаем:
		user = TelehooperUser(
			self,
			(await self.TGBot.get_chat_member(user_id, user_id)).user
		)
		await user.restoreFromDB()

		self.telehooperbotUsers.append(user)

		return user

	def addDialogueGroup(self, group: DialogueGroup) -> List[DialogueGroup]:
		"""
		Добавляет диалог-группу в бота.
		"""

		# TODO: Перенести в MAPI?

		self.dialogueGroupsList.append(group)

		# Получаем ДБ:
		DB = getDefaultCollection()

		DB.update_one({
				"_id": "_global"
			}, {
				"$push": {
					"ServiceDialogues.VK": {
						"ID": group.serviceDialogueID,
						"TelegramGroupID": group.group.id,
						"AddDate": datetime.datetime.now(),
						"LatestMessageID": None,
						"LatestServiceMessageID": None
						# TODO: "PinnedMessageID": group.pinnedMessageID
					}
				}
			},

			upsert=True
		)

		return self.dialogueGroupsList

	async def retrieveDialogueListFromDB(self) -> List[DialogueGroup]:
		"""
		Достаёт список групп-диалогов из ДБ, и сохраняет в "кэш".
		"""

		# Получаем ДБ:
		DB = getDefaultCollection()

		res = DB.find_one({
			"_id": "_global"
		})
		if res:
			old_dialogueList = self.dialogueGroupsList.copy()

			newList = []
			for dialogue in res["ServiceDialogues"]["VK"]:
				# Ищем группу в кэше:
				for oldDialogue in old_dialogueList:
					if oldDialogue.serviceDialogueID == dialogue["ID"]:
						newList.append(oldDialogue)
						break
				else:
					# Если группы нет в кэше, то создаём новую:
					newDialogue = DialogueGroup(
						await self.TGBot.get_chat(dialogue["TelegramGroupID"]),
						dialogue["ID"]
					)
					newList.append(newDialogue)

			# Каждый диалог, находящийся в переменной, добавляем:
			self.dialogueGroupsList = []
			self.dialogueGroupsList.extend(newList)

		return self.dialogueGroupsList

	async def getDialogueGroupByTelegramGroup(self, telegram_group: aiogram.types.Chat | int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		await self.retrieveDialogueListFromDB()

		if isinstance(telegram_group, aiogram.types.Chat):
			telegram_group = telegram_group.id

		for group in self.dialogueGroupsList:
			if group.group.id == telegram_group:
				return group

		return None

	async def getDialogueGroupByServiceDialogueID(self, service_dialogue_id: aiogram.types.Chat | int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по её ID в сервисе, либо же `None`, если ничего не было найдено.
		"""

		await self.retrieveDialogueListFromDB()

		for group in self.dialogueGroupsList:
			if group.serviceDialogueID == service_dialogue_id:
				return group

		return None

	def saveLatestMessageID(self, dialogue_telegram_id: int | str, telegram_message_id: int | str, service_message_id: int | str) -> None:
		"""
		Сохраняет в ДБ ID последнего сообщения в диалоге.
		"""

		DB = getDefaultCollection()
		DB.update_one({"_id": "_global"}, {
			"$set": {
				"ServiceDialogues.VK.$[element].LatestMessageID": telegram_message_id,
				"ServiceDialogues.VK.$[element].LatestServiceMessageID": service_message_id
			}
		}, array_filters = [{"element.TelegramGroupID": dialogue_telegram_id}])

	def getLatestMessageID(self, dialogue_telegram_id: int | str) -> Tuple[int, int] | None:
		"""
		Возвращает ID последнего сообщения в диалоге.
		"""

		# TODO
		# DB = getDefaultCollection()
		# # res = DB.find_one({"_id": "_global", "ServiceDialogues.VK.$[element].TelegramGroupID": dialogue_telegram_id}, array_filters=[{"element.TelegramGroupID": dialogue_telegram_id}])
		# res = DB.find_one({"_id": "_global", "ServiceDialogues.VK.TelegramGroupID": dialogue_telegram_id}, {"ServiceDialogues.VK.LatestServiceMessageID": 1, "ServiceDialogues.VK.LatestMessageID": 1, "ServiceDialogues.VK.TelegramGroupID": 1})

		# if res:
		# 	return res["ServiceDialogues"]["VK"][0]["LatestMessageID"], res["ServiceDialogues"]["VK"][0]["LatestServiceMessageID"]

		# return None


	def __str__(self) -> str:
		return f"<TelehooperBot id{self.TGBot.id}>"

class Minibot:
	"""
	Класс мини-бота.
	"""

	token: str
	parse_mode: str
	storage: MemoryStorage

	MainBot: Telehooper
	TGBot: aiogram.Bot
	DP: aiogram.Dispatcher

	def __init__(self, main_telegram_bot: Telehooper, telegram_bot_token: str, telegram_bot_parse_mode: str = aiogram.types.ParseMode.HTML, storage: Optional[MemoryStorage] = None) -> None: # type: ignore
		self.MainBot = main_telegram_bot
		self.token = telegram_bot_token
		self.parse_mode = telegram_bot_parse_mode

		if storage is None:
			self.storage = MemoryStorage()
		else:
			self.storage = storage


	def initTelegramBot(self, add_to_main_bot: bool = True) -> Tuple[aiogram.Bot, aiogram.Dispatcher]:
		"""
		Инициализирует Telegram бота.
		"""

		# Инициализируем Telegram-бота:
		Bot = aiogram.Bot(
			token       = self.token,
			parse_mode  = self.parse_mode
		)

		# Создаём Dispatcher:
		DP = aiogram.Dispatcher(Bot, storage=self.storage)

		# Сохраняем в класс:
		self.DP = DP
		self.TGBot = Bot

		# Инициализируем все команды (handler'ы):
		self.initTelegramBotHandlers()

		# Добавляем бота в главный бот:
		if add_to_main_bot:
			self.MainBot.addMinibot(self)

		return Bot, DP

	def initTelegramBotHandlers(self) -> None:
		"""
		Инициализирует все handler'ы для Мультибота.
		"""

		from TelegramMultibotHandlers import DMMessage
		importHandlers([DMMessage], self, is_multibot=True, mainBot=self.MainBot)

		self.DP.errors_handler()(global_error_handler)

class DialogueGroup:
	"""
	Класс, отображающий объект группы-диалога в Telegram.
	"""

	group: aiogram.types.Chat
	serviceType: int
	serviceDialogueID: int


	def __init__(self, group: aiogram.types.Chat, service_dialogue_id: int) -> None:
		self.group = group
		self.serviceType = MAPIServiceType.VK
		self.serviceDialogueID = service_dialogue_id

	def __str__(self) -> str:
		return f"<DialogueGroup serviceID:{self.serviceType} ID:{self.serviceDialogueID}>"

async def global_error_handler(update: aiogram.types.Update, exception) -> bool:
	"""
	Глобальный обработчик ВСЕХ ошибок у бота.
	"""

	if isinstance(exception, aiogram.utils.exceptions.Throttled):
		await update.message.answer("⏳ Превышен лимит количества запросов использования команды. Попробуй позже.")
	elif isinstance(exception, Exceptions.CommandAllowedOnlyInGroup):
		await update.message.answer("⚠️ Данную команду можно использовать только в Telegram-группах.")
	elif isinstance(exception, Exceptions.CommandAllowedOnlyInPrivateChats):
		await update.message.answer(f"⚠️ Данную команду можно использовать только {(await update.bot.get_me()).get_mention('в личном диалоге с ботом', as_html=True)}.")
	elif isinstance(exception, Exceptions.CommandAllowedOnlyInBotDialogue):
		await update.message.answer("⚠️ Данную команду можно использовать только в диалоге подключённого сервиса.\n\n⚙️ Используй команду /help, что бы узнать, как создать диалог сервиса.")
	else:
		logger.exception(exception)

		await update.bot.send_message(update.callback_query.message.chat.id, f"<b>Что-то пошло не так 😕\n\n</b>У бота произошла внутренняя ошибка: \n<code>{exception}\n</code>Попробуй позже. Если ошибка повторяется, сделай баг репорт в <a href=\"https://github.com/Zensonaton/Telehooper/issues\">Issue</a> проекта.")

	return True

def importHandlers(handlers, bot: Telehooper | Minibot, mainBot: Optional[Telehooper] = None, is_multibot: bool = False) -> None:
	"""
	Загружает (импортирует?) все Handler'ы в бота.
	"""

	MESSAGE_HANDLERS_IMPORTED = handlers
	MESSAGE_HANDLERS_IMPORTED_FILENAMES = [i.__name__.split(".")[-1] + ".py" for i in MESSAGE_HANDLERS_IMPORTED]

	# Загружаем команды.
	logger.debug(f"Было импортировано {len(MESSAGE_HANDLERS_IMPORTED)} handler'ов, загружаю их...")

	# Предупреждение, если был найден .py файл, но он не был импортирован выше:
	files_found = [i for i in os.listdir("src/" + ("TelegramMultibotHandlers" if is_multibot else "TelegramBotHandlers")) if i.endswith(".py") and not i == "__init__.py"]
	files_not_imported = [i for i in files_found if i not in MESSAGE_HANDLERS_IMPORTED_FILENAMES]

	if files_not_imported:
		logger.warning(f"Был обнаружен файл \"{(', '.join(files_not_imported))}\" в папке с handler'ами, и он не был загружен в программу, поскольку импорт не был выполнен в коде файла TelegramBot.py!")

	for index, messageHandler in enumerate(MESSAGE_HANDLERS_IMPORTED):
		messageHandler._setupCHandler(bot)

		logger.debug(f"Инициализирован обработчик команды \"{MESSAGE_HANDLERS_IMPORTED_FILENAMES[index]}\".")

	logger.debug(f"Все handler'ы были загружены успешно!")

# coding: utf-8

# Код для логики Telegram-бота.

from __future__ import annotations

import logging
import os
from typing import List, Optional

import aiogram
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import Exceptions
from TelegramBotHandlers import OtherCallbackQueryHandlers
from MiddlewareAPI import TelehooperUser
from Consts import MAPIServiceType
from DB import getDefaultCollection

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


	def __init__(self, telegram_bot_token: str, telegram_bot_parse_mode: str = aiogram.types.ParseMode.HTML, storage: Optional[MemoryStorage] = None):
		self.token = telegram_bot_token
		self.parse_mode = telegram_bot_parse_mode

		self.miniBots = []

		self.telehooperbotUsers = []
		self.dialogueGroupsList = []

		if storage is None:
			self.storage = MemoryStorage()
		else:
			self.storage = storage


	def initTelegramBot(self):
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

	def initTelegramBotHandlers(self):
		"""
		Инициализирует все handler'ы бота.
		"""

		# Импортируем все Handler'ы как модули:
		from TelegramBotHandlers import (ConvertToPublicServiceDialogue,
		                                 ConvertToServiceDialogue, Dialogue,
		                                 GroupEvents, Services, Setup, Start,
		                                 VKLogin, Debug, This, Connect)

		# А теперь добавляем их в бота:
		importHandlers([Setup, Start, VKLogin, Services, GroupEvents, ConvertToServiceDialogue, ConvertToPublicServiceDialogue, OtherCallbackQueryHandlers, Dialogue, Debug, This, Connect], self, is_multibot=False)
		# TODO: Что-то сделать с этим срамом. Это ужасно.


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
			(await self.TGBot.get_chat_member(user_id, user_id)).user
		)
		await user.restoreFromDB()

		self.telehooperbotUsers.append(user)

		return user

	def addDialogueGroup(self, group: DialogueGroup):
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
					"TelegramGroupID": group.group.id
				}
			}
		},
		upsert=True
		)

	def getDialogueGroupByTelegramGroup(self, telegram_group: aiogram.types.Chat | int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram.
		"""

		if isinstance(telegram_group, aiogram.types.Chat):
			telegram_group = telegram_group.id

		for group in self.dialogueGroupsList:
			if group.group.id == telegram_group:
				return group

		return None

	def getDialogueGroupByServiceDialogueID(self, service_dialogue_id: aiogram.types.Chat | int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по её ID в сервисе.
		"""

		for group in self.dialogueGroupsList:
			if group.group.id == service_dialogue_id:
				return group

		return None

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

	def __init__(self, main_telegram_bot: Telehooper, telegram_bot_token: str, telegram_bot_parse_mode: str = aiogram.types.ParseMode.HTML, storage: Optional[MemoryStorage] = None) -> None:
		self.MainBot = main_telegram_bot
		self.token = telegram_bot_token
		self.parse_mode = telegram_bot_parse_mode

		if storage is None:
			self.storage = MemoryStorage()
		else:
			self.storage = storage


	def initTelegramBot(self, add_to_main_bot: bool = True):
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


	def initTelegramBotHandlers(self):
		"""
		Инициализирует все handler'ы для Мультибота.
		"""

		from TelegramMultibotHandlers import DMMessage, Test
		importHandlers([Test, DMMessage], self, is_multibot=True, mainBot=self.MainBot)

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

async def global_error_handler(update, exception):
	"""
	Глобальный обработчик ВСЕХ ошибок у бота.
	"""

	if isinstance(exception, aiogram.utils.exceptions.Throttled):
		await update.message.answer("⏳ Превышен лимит количества запросов использования команды. Попробуй позже.")
	elif isinstance(exception, Exceptions.CommandAllowedOnlyInGroup):
		await update.message.answer("⚠️ Данную команду можно использовать только в Telegram-группах.")
	elif isinstance(exception, Exceptions.CommandAllowedOnlyInPrivateChats):
		await update.message.answer("⚠️ Данную команду можно использовать только в личном диалоге с ботом.")
	elif isinstance(exception, Exceptions.CommandAllowedOnlyInBotDialogue):
		await update.message.answer("⚠️ Данную команду можно использовать только в диалоге подключённого сервиса.\n\n⚙️ Попробуй присоеденить диалог сервиса к группе Telegram, используя команду /setup.")
	else:
		logger.exception(exception)

		await update.message.answer(f"⚠️ Произошла ошибка: <code>{exception}</code>.\nПопробуй позже.\n\nТак же, ты можешь зарепортить баг в <a href=\"https://github.com/Zensonaton/Telehooper/issues\">Issues</a> проекта.")

	return True

def importHandlers(handlers, bot: Telehooper | Minibot, mainBot: Optional[Telehooper] = None, is_multibot: bool = False):
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

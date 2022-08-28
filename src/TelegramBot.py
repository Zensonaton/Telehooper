# coding: utf-8

# Код для логики Telegram-бота.

from __future__ import annotations
from asyncio import Task
import asyncio

import datetime
from typing import Any, List, Literal, Optional, Tuple, cast

import aiogram
import vkbottle
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from loguru import logger
from vkbottle_types.responses.account import AccountUserSettings

import Exceptions
from DB import getDefaultCollection
from ServiceAPIs.Base import DialogueGroup
from ServiceAPIs.VK import VKDialogue, VKTelehooperAPI
from TelegramBotHandlers.commands import MD

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

	vkAPI: VKTelehooperAPI | None

	def __init__(self, telegram_bot_token: str, telegram_bot_parse_mode = aiogram.types.ParseMode.HTML, storage: Optional[MemoryStorage] = None) -> None:
		self.token = telegram_bot_token
		self.parse_mode = telegram_bot_parse_mode # type: ignore

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
		from TelegramBotHandlers import OtherCallbackQueryHandlers
		from TelegramBotHandlers.commands import (Help, Self, Start, This,
		                                          VKLogin, Debug)
		from TelegramBotHandlers.events import GroupEvents, RegularMessageHandlers

		# А теперь добавляем их в бота:
		self.importHandlers([Start, VKLogin, GroupEvents, OtherCallbackQueryHandlers, This, Self, RegularMessageHandlers, MD, Help, Debug], self, is_multibot=False)

		# Отдельно добавляю Error Handler:
		self.DP.errors_handler()(self.global_error_handler)

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

		if not res:
			return []

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

	def importHandlers(self, handlers, bot: Telehooper | Minibot, mainBot: Optional[Telehooper] = None, is_multibot: bool = False) -> None:
		"""
		Загружает (импортирует?) все Handler'ы в бота.
		"""

		MESSAGE_HANDLERS_IMPORTED_FILENAMES = [i.__name__.split(".")[-1] + ".py" for i in handlers]

		# Загружаем команды.
		logger.debug(f"Было импортировано {len(handlers)} handler'ов, загружаю их...")

		for index, messageHandler in enumerate(handlers):
			messageHandler._setupCHandler(bot)

			logger.debug(f"Инициализирован обработчик команды \"{handlers[index]}\".")

		logger.debug(f"Все handler'ы были загружены успешно!")

	async def global_error_handler(self, update: aiogram.types.Update, exception) -> bool:
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

			await update.bot.send_message(update.message.chat.id, f"<b>Что-то пошло не так 😕\n\n</b>У бота произошла внутренняя ошибка:\n<code>{exception}\n</code>\n\nℹ️ Попробуй позже. Если ошибка повторяется, сделай баг репорт в <a href=\"https://github.com/Zensonaton/Telehooper/issues\">Issue</a> проекта.")

		return True

	async def sendMessage(self, user: TelehooperUser, text: str | None, chat_id: int | None = None, attachments: list | None = [], reply_to: int | None = None, allow_sending_temp_messages: bool = True, return_only_first_element: bool = True):
		"""
		Отправляет сообщение в Telegram.
		"""

		def _return(variable):
			"""
			Возвращает первый элемент, если это массив, и `return_only_first_element` - True.
			"""

			if return_only_first_element and isinstance(variable, list):
				return variable[0]
			else:
				return variable

		# Фиксы:
		if attachments is None:
			attachments = []

		if text is None:
			text = ""

		if chat_id is None:
			chat_id = user.TGUser.id

		reply_to = reply_to if reply_to is None else int(reply_to)

		self.vkAPI = cast(VKTelehooperAPI, self.vkAPI)

		# Проверяем, есть ли у нас вложения, которые стоит отправить:
		if len(attachments) > 0:
			tempMediaGroup = aiogram.types.MediaGroup()
			loadingCaption = "<i>Весь контент появится здесь после загрузки, подожди...</i>\n\n" + text

			# Если мы можем отправить временные сообщения, то отправляем их:
			if allow_sending_temp_messages and len(attachments) > 1:

				tempImageFileID: str | None = None
				tempMessages: List[aiogram.types.Message] = []
				DB = getDefaultCollection()

				# Пытаемся достать fileID временной фотки из ДБ:
				res = DB.find_one({"_id": "_global"})
				if res:
					tempImageFileID = res["TempDownloadImageFileID"]

				# Добавляем временные вложения:
				for index in range(len(attachments)):

					# Проверяем, есть ли у нас в ДБ идентификатор для временного файла. Если да,
					# то добавляем caption только на первом элементе, в ином случае Telegram
					# не покажет нам текст сообщения.
					#
					# Как бы я не хвалил Telegram, технические решения здесь отвратительны.
					if tempImageFileID:
						tempMediaGroup.attach(
							aiogram.types.InputMediaPhoto(tempImageFileID, loadingCaption if index == 0 else None)
						)
					else:
						tempMediaGroup.attach(
							aiogram.types.InputMediaPhoto(
								aiogram.types.InputFile("downloadImage.png"), 
								loadingCaption if index == 0 else None
							)
						)

						# Что бы не грузить одну временную фотку множество раз, делаем так:
						tempImageFileID = tempMessages[0].photo[-1].file_id

						# А так же, обязательно сохраняем fileID временной фотки в ДБ:
						DB.update_one({"_id": "_global"}, {
							"$set": {
								"TempDownloadImageFileID": tempMessages[0].photo[-1].file_id
							}
						})

				# Отправляем файлы с временными сообщениями, которые мы заменим реальными вложениями.
				tempMessages = await self.TGBot.send_media_group(chat_id, tempMediaGroup, reply_to_message_id=reply_to)

				# Спим, ибо flood control.
				await asyncio.sleep(3)

				# Теперь нам стоит отредачить сообщение с новыми вложениями.
				# Я специально редактирую всё с конца, что бы не трогать лишний раз caption
				# самого первого сообщения.
				for index, attachment in reversed(list(enumerate(attachments))):
					await self.vkAPI.startDialogueActivity(user, chat_id, "photo")

					# Загружаем файл, если он не был загружен:
					if not attachment.ready:
						await attachment.parse()

					# Заменяем старый временный файл на новый:
					await tempMessages[index].edit_media(
						aiogram.types.InputMedia(
							media=attachment.aiofile, 
							caption=text if index == 0 else None
						)
					)

					# Каждый запрос спим, что бы не превысить лимит:
					await asyncio.sleep(1.5)

				return _return(tempMessages)
			else:
				# Если мы не можем отправить временные сообщения, то добавляем их по одному в MediaGroup:

				for index, attachment in enumerate(attachments):
					if not attachment.ready:
						await attachment.parse()

					MEDIA_TYPES = ["photo", "video", "document", "animation"]

					if attachment.type in MEDIA_TYPES:
						tempMediaGroup.attach(aiogram.types.InputMedia(media=attachment.aiofile, caption=text if index == 0 else None))
					elif attachment.type == "voice":
						return _return(await self.TGBot.send_voice(chat_id, attachment.aiofile, reply_to_message_id=reply_to))



				# И после добавления в MediaGroup, отправляем сообщение:
				await self.vkAPI.startDialogueActivity(user, chat_id, "photo")

				return _return(await self.TGBot.send_media_group(chat_id, tempMediaGroup, reply_to_message_id=reply_to))

		# У нас нет никакой группы вложений, поэтому мы просто отправим сообщение:
		return _return(await self.TGBot.send_message(chat_id, text, reply_to_message_id=reply_to))

	async def editMessage(self, user: TelehooperUser, text: str | None, chat_id: int, message_id: str | int, attachments: list | None = []):
		"""
		Редактирует сообщение в Telegram.
		"""

		if text is None:
			text = ""

		if message_id is str:
			message_id = int(message_id)
		message_id = cast(int, message_id)

		if attachments is None:
			attachments = []

		# await self.TGBot.edit_message_text(f"{text}      <i>✏️ изменено...</i>", chat_id, message_id)
		await self.TGBot.edit_message_text(f"{text}      <i>(ред.)</i>", chat_id, message_id)

	async def startDialogueActivity(self, chat_id: int, activity_type: Literal["typing", "upload_photo", "record_video", "upload_video", "record_voice", "upload_voice", "upload_document", "choose_sticker", "find_location", "record_video_note", "upload_video_note"] = "typing"):
		await self.TGBot.send_chat_action(chat_id, action=activity_type)

	async def saveCachedResource(self, service_name: str, resource_input: str, resource_output: str):
		"""
		Сохраняет ресурс в кэш. Это необходимо для кэширования, к примеру, стикеров.
		"""

		DB = getDefaultCollection()

		DB.update_one({
				"_id": "_global"
			},

			{

			}
		)


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
		self.MainBot.importHandlers([DMMessage], self, is_multibot=True, mainBot=self.MainBot)

		self.DP.errors_handler()(self.MainBot.global_error_handler)

class TelehooperUser:
	"""
	Класс, отображающий пользователя бота Telehooper: тут будут все подключённые сервисы.
	"""

	TGUser: aiogram.types.User
	bot: Telehooper

	vkAPI: vkbottle.API
	vkUser: vkbottle.User

	APIstorage: TelehooperAPIStorage

	def __init__(self, bot: Telehooper, user: aiogram.types.User) -> None:
		self.TGUser = user
		self.bot = bot
		self.isVKConnected = False
		self.APIstorage = TelehooperAPIStorage()


	async def restoreFromDB(self) -> None:
		"""
		Восстанавливает данные, а так же подключенные сервисы из ДБ.
		"""

		DB = getDefaultCollection()

		res = DB.find_one({"_id": self.TGUser.id})
		if res and res["Services"]["VK"]["Auth"]:
			# Аккаунт ВК подключён.

			# Подключаем ВК:
			# await self.connectVKAccount(res["Services"]["VK"]["Token"], res["Services"]["VK"]["IsAuthViaPassword"])
			# TODO?
			pass

	async def getDialogueGroupByTelegramGroup(self, telegram_group: aiogram.types.Chat | int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		return await self.bot.getDialogueGroupByTelegramGroup(telegram_group)

	async def getDialogueGroupByServiceDialogueID(self, service_dialogue_id: int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		return await self.bot.getDialogueGroupByServiceDialogueID(service_dialogue_id)

	def __str__(self) -> str:
		return f"<TelehooperUser id:{self.TGUser.id}>"

class TelehooperAPIStorage:
	"""
	Класс для хранения некоторой важной для сервисов информации.
	"""

	class VKAPIStorage:
		"""
		Класс для хранения важной для VK API информации.
		"""

		accountInfo: AccountUserSettings = None # type: ignore
		fullUserInfo: Any = None # type: ignore # FIXME: Удалить это поле?
		pollingTask: Task = None # type: ignore
		dialogues: List[VKDialogue] = []

	vk: VKAPIStorage

	def __init__(self) -> None:
		self.vk = self.VKAPIStorage()

class CachedResource:
	"""
	Класс, отображающий кэшированный ресурс.
	"""

	input: str
	output: str

	def __init__(self, input: str, output: str) -> None:
		self.input = input
		self.output = output

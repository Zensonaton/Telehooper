# coding: utf-8

# Код для логики Telegram-бота.

from __future__ import annotations

import asyncio
import datetime
from asyncio import Task
from typing import Any, List, Optional, Tuple, cast

import aiogram
import vkbottle
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from vkbottle_types.responses.account import AccountUserSettings
from vkbottle_types.responses.users import UsersUserFull

import Exceptions
import Utils
from Consts import SETTINGS, InlineButtonCallbacks as CButtons
from DB import getDefaultCollection
from ServiceAPIs.Base import DialogueGroup
from ServiceAPIs.VK import VKDialogue, VKTelehooperAPI
from Settings import SettingsHandler


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

	settingsHandler: SettingsHandler

	vkAPI: VKTelehooperAPI | None

	def __init__(self, telegram_bot_token: str, telegram_bot_parse_mode = aiogram.types.ParseMode.HTML, storage: Optional[MemoryStorage] = None, settings_tree: dict = SETTINGS) -> None:
		self.token = telegram_bot_token
		self.parse_mode = telegram_bot_parse_mode # type: ignore

		self.miniBots = []

		self.telehooperbotUsers = []
		self.dialogueGroupsList = []

		if storage is None:
			self.storage = MemoryStorage()
		else:
			self.storage = storage

		self.settingsHandler = SettingsHandler(settings_tree)


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
		from TelegramBotHandlers.commands import (MD, Debug, Help, Self, Settings,
		                                          Start, This, VKLogin, MarkAsRead)
		from TelegramBotHandlers.events import GroupEvents, RegularMessageHandlers

		# А теперь добавляем их в бота:
		self.importHandlers([
				Start, VKLogin, This, Self, MD, Help, Debug, Settings, MarkAsRead, 
				RegularMessageHandlers, GroupEvents, OtherCallbackQueryHandlers
			], 
			self, 
			is_multibot=False
		)

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

		self.telehooperbotUsers.append(user)

		return user

	def addDialogueGroup(self, group: DialogueGroup) -> List[DialogueGroup]:
		"""
		Добавляет диалог-группу в бота.
		"""

		self.dialogueGroupsList.append(group)

		# Получаем ДБ:
		DB = getDefaultCollection()

		DB.update_one(
			{
				"_id": "_global"
			}, 
			
			{
				"$push": {
					"ServiceDialogues.VK": {
						"ID": group.serviceDialogueID,
						"TelegramGroupID": group.group.id,
						"AddDate": datetime.datetime.now(),
						"LatestMessageID": None,
						"LatestServiceMessageID": None,
						"PinnedMessageID": group.group.pinned_message.message_id
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
			try:
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
			except:
				# Бота исключили из группы.

				# TODO: Удалить из БД.

				pass

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

	def getDialoguePin(self, service_name: str, telegram_group: aiogram.types.Chat | int) -> int | None:
		"""
		Достаёт закреплённое сообщение из диалога, выдавая его ID.
		"""

		if isinstance(telegram_group, aiogram.types.Chat):
			telegram_group = telegram_group.id

		DB = getDefaultCollection()

		res = DB.find_one(
			{
				f"ServiceDialogues.{service_name}.TelegramGroupID": telegram_group
			},

			{
				f"ServiceDialogues.{service_name}.$": 1, "_id": 0
			}
		)
		if not res:
			return None

		res = res["ServiceDialogues"][service_name][0]

		return res.get("PinnedMessageID", None)

	def importHandlers(self, handlers: list, bot: Telehooper | Minibot, mainBot: Optional[Telehooper] = None, is_multibot: bool = False) -> None:
		"""
		Загружает (импортирует?) все Handler'ы в бота.
		"""

		MESSAGE_HANDLERS_IMPORTED_FILENAMES = [i.__name__.split(".")[-1] + ".py" for i in handlers]

		# Загружаем команды.
		logger.debug(f"Было импортировано {len(handlers)} handler'ов, загружаю их...")

		for index, messageHandler in enumerate(handlers):
			messageHandler._setupHandler(bot)

			logger.debug(f"Инициализирован обработчик команды \"{handlers[index].__name__}\".")

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

	async def sendMessage(self, user: TelehooperUser, text: str | None, chat_id: int | None = None, attachments: list[Utils.File] | None = [], reply_to: int | None = None, allow_sending_temp_messages: bool = True, return_only_first_element: bool = True, read_button: bool = True):
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

		keyboard = InlineKeyboardMarkup()

		if read_button:
			keyboard.add(
				InlineKeyboardButton(
					"Прочитать",
					callback_data=CButtons.CommandCallers.MARK_AS_READ
				)
			)

		# Проверяем, есть ли у нас вложения, которые стоит отправить:
		if len(attachments) > 0:
			tempMediaGroup = aiogram.types.MediaGroup()
			loadingCaption = "<i>Весь контент появится здесь после загрузки, подожди...</i>\n\n" + text

			# Если мы можем отправить временные сообщения, то отправляем их:
			if allow_sending_temp_messages and len(attachments) > 1:
				tempImageFileID: str | None = None
				tempMessages: List[aiogram.types.Message] = []
				indeciesInCache = []

				DB = getDefaultCollection()

				# Пытаемся достать fileID временной фотки из ДБ:
				res = DB.find_one({"_id": "_global"})
				if res:
					tempImageFileID = res["TempDownloadImageFileID"]

				# Добавляем временные вложения:
				for index, attachment in enumerate(attachments):
					# Пытаемся достать кэш:
					cache =	self.getCachedResource(
						"VK",
						cast(str, attachment.uid)
					)

					if cache:
						# Кэш есть, дешифровываем.

						cache = Utils.decryptWithKey(
							cache,
							cast(str, attachment.uid)
						)

						tempMediaGroup.attach(
							aiogram.types.InputMedia(
								media=cache,
								caption=loadingCaption if index == 0 else None
							)
						)

						indeciesInCache.append(index)

						continue


					# Проверяем, есть ли у нас в ДБ идентификатор для временного файла. Если да,
					# то добавляем caption только на первом элементе, в ином случае Telegram
					# не покажет нам текст сообщения.
					#
					# Как бы я не хвалил Telegram, технические решения здесь отвратительны.
					tempMediaGroup.attach(
						aiogram.types.InputMediaPhoto(
							tempImageFileID if tempImageFileID else aiogram.types.InputFile("resources/downloadImage.png"), 
							loadingCaption if index == 0 else None
						)
					)

				# Отправляем файлы с временными сообщениями, которые мы заменим реальными вложениями.
				tempMessages = await self.TGBot.send_media_group(
					chat_id, 
					tempMediaGroup, 
					reply_to_message_id=reply_to,
				)

				if not tempImageFileID:
					# Что бы не грузить одну временную фотку множество раз, делаем так:
					tempImageFileID = tempMessages[0].photo[-1].file_id

					# И обязательно сохраняем fileID временной фотки в ДБ:
					DB.update_one({"_id": "_global"}, {
						"$set": {
							"TempDownloadImageFileID": tempImageFileID
						}
					})

				del tempImageFileID

				if len(indeciesInCache) != len(attachments):
					# Спим, ибо flood control.
					await asyncio.sleep(3)

				# Теперь нам стоит отредачить сообщение с новыми вложениями.
				# Я специально редактирую всё с конца, что бы не трогать лишний раз caption
				# самого первого сообщения.
				for index, attachment in reversed(list(enumerate(attachments))):
					# Если такое изображение уже было кэшировано, ничего не делаем.

					if index in indeciesInCache:
						await tempMessages[index].edit_caption(text)

						continue

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
					cache = self.getCachedResource(
						"VK",
						Utils.sha256hash(cast(str, attachment.uid))
					)

					if cache:
						# Ресурс есть в кэше.

						cache = Utils.decryptWithKey(
							cache,
							cast(str, attachment.uid)
						)

					if not attachment.ready and not cache:
						await attachment.parse()

					MEDIA_TYPES = ["photo", "document", "animation"]

					if attachment.type in MEDIA_TYPES:
						tempMediaGroup.attach(
							aiogram.types.InputMedia(media=cache if cache else attachment.aiofile, caption=text if index == 0 else None)
						)
					elif attachment.type == "voice":
						# В сообщении может быть только одно голосовое сообщение.

						return _return(
							await self.TGBot.send_voice(chat_id, cache if cache else attachment.aiofile, reply_to_message_id=reply_to, reply_markup=keyboard)
						)
					elif attachment.type == "video":
						tempMediaGroup.attach(
							aiogram.types.InputMediaVideo(media=cache if cache else attachment.aiofile, caption=text if index == 0 else None)
						)
					elif attachment.type == "sticker":
						# В сообщении может быть только один стикер.
						
						msg = await self.TGBot.send_sticker(chat_id, sticker=cache if cache else attachment.aiofile, reply_to_message_id=reply_to, reply_markup=keyboard)

						# Кэшируем стикер:
						self.saveCachedResource(
							"VK",
							Utils.sha256hash(cast(str, attachment.uid)),
							Utils.encryptWithKey(
								msg.sticker.file_id,
								cast(str, attachment.uid)
							)
						)

						return _return(msg)
					else:
						raise Exception(f"Неизвестный тип {attachment.type}")



				await self.TGBot.send_chat_action(chat_id, "upload_photo")

				# И после добавления в MediaGroup, отправляем сообщение:
				mediaMessages = await self.TGBot.send_media_group(chat_id, tempMediaGroup, reply_to_message_id=reply_to)
				
				# Кэшируем всё, что есть:
				for index, msg in enumerate(mediaMessages):
					media = getattr(msg, cast(str, msg.content_type))
					if msg.content_type == "photo":
						media = media[-1]

					self.saveCachedResource(
						"VK",
						Utils.sha256hash(cast(str, attachments[index].uid)),
						Utils.encryptWithKey(
							media.file_id,
							cast(str, attachments[index].uid)
						)
					)

				return _return(mediaMessages)

		# У нас нет никакой группы вложений, поэтому мы просто отправим сообщение:
		return _return(await self.TGBot.send_message(chat_id, text, reply_to_message_id=reply_to, reply_markup=keyboard))

	async def editMessage(self, user: TelehooperUser, text: str | None, chat_id: int, message_id: int, attachments: list | None = []):
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

		await self.TGBot.edit_message_text(f"{text}      <i>(ред.)</i>", chat_id, message_id)

	async def deleteMessage(self, user: TelehooperUser, chat_id: int, message_id: int):
		"""
		Удаляет сообщение в Telegram.
		"""

		await self.TGBot.delete_message(chat_id, message_id)

	def saveCachedResource(self, service_name: str, resource_input: str, resource_output: str):
		"""
		Сохраняет ресурс в кэш. Это необходимо для кэширования, к примеру, стикеров.
		"""

		DB = getDefaultCollection()

		resource_input = resource_input.replace(".", "_")

		DB.update_one(
			{
				"_id": "_global"
			},

			{
				"$set": {
					f"ResourceCache.{service_name}.{resource_input}": resource_output
				}
			},

			upsert=True
		)

	def getCachedResource(self, service_name: str, resource_input: str) -> None | str:
		"""
		Вытаскивает значение ресурса из кэша. Может вернуть `None`, если такое значение не было найдено.
		"""

		DB = getDefaultCollection()

		resource_input = resource_input.replace(".", "_")

		res = DB.find_one(
			{
				"_id": "_global"
			}
		)
		if not res:
			return None

		for key, value in res["ResourceCache"][service_name].items():
			if key == resource_input:
				return value

		return None	


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
	telehooperBot: Telehooper

	vkAPI: vkbottle.API
	vkUser: vkbottle.User

	APIstorage: TelehooperAPIStorage

	def __init__(self, bot: Telehooper, user: aiogram.types.User) -> None:
		self.TGUser = user
		self.telehooperBot = bot
		self.isVKConnected = False
		self.APIstorage = TelehooperAPIStorage()

	async def getDialogueGroupByTelegramGroup(self, telegram_group: aiogram.types.Chat | int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		return await self.telehooperBot.getDialogueGroupByTelegramGroup(telegram_group)

	async def getDialogueGroupByServiceDialogueID(self, service_dialogue_id: int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		return await self.telehooperBot.getDialogueGroupByServiceDialogueID(service_dialogue_id)

	def getDialoguePin(self, telegram_group: aiogram.types.Chat | int):
		return self.telehooperBot.getDialoguePin("VK", telegram_group)

	def getSetting(self, path: str) -> Any:
		return self.telehooperBot.settingsHandler.getUserSetting(self, path)

	def setSetting(self, path: str, new_value: Any) -> Any:
		return self.telehooperBot.settingsHandler.setUserSetting(self, path, new_value)

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
		fullUserInfo: UsersUserFull = None # type: ignore
		pollingTask: Task = None # type: ignore
		dialogues: List[VKDialogue] = []

	vk: VKAPIStorage

	def __init__(self) -> None:
		self.vk = self.VKAPIStorage()

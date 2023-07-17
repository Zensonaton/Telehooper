# coding: utf-8

import asyncio
from typing import Any

import aiohttp
from aiocouch import Document
from aiogram import Bot
from aiogram.types import BufferedInputFile, Chat, Message, User

import utils
from config import config
from DB import get_db, get_default_subgroup, get_group
from DB import get_user as db_get_user
from exceptions import DisallowedInDebugException
from services.service_api_base import BaseTelehooperServiceAPI, ServiceDialogue
from services.vk.service import VKServiceAPI
from settings import SETTINGS_TREE, SettingsHandler


# Да, я знаю что это плохой способ. Знаю. Ни к чему другому, адекватному я не пришёл.
_saved_connections = {}
_service_dialogues: list["TelehooperSubGroup"] = []

settings = SettingsHandler(SETTINGS_TREE)

class TelehooperUser:
	"""
	Пользователь бота Telehooper.
	"""

	id: int
	username: str | None
	name: str
	creationDate: int
	botBanned: bool
	settingsOverriden: dict
	knownLanguage: str | None
	roles: list[str]
	connections: dict

	rawDocument: Document
	telegramUser: User

	def __init__(self, rawDocument: Document, telegramUser: User) -> None:
		self.rawDocument = rawDocument
		self.telegramUser = telegramUser
		self._parse_document(rawDocument)

	def _parse_document(self, user: Document) -> None:
		"""
		Парсит значение документа пользователя в объект пользователя.
		"""

		self.id = user["ID"]
		self.username = user["Username"]
		self.name = user["Name"]
		self.creationDate = user["CreationDate"]
		self.botBanned = user["BotBanned"]
		self.settingsOverriden = user["SettingsOverriden"]
		self.knownLanguage = user["KnownLanguage"]
		self.roles = user["Roles"]
		self.connections = user["Connections"]

	async def refresh_document(self) -> Document:
		"""
		Обновляет документ пользователя из БД.
		"""

		self.rawDocument = await db_get_user(self.telegramUser)
		self._parse_document(self.rawDocument)

		return self.rawDocument

	def _get_service_store_name(self, name: str) -> str:
		"""
		Возвращает название ключа в словаре `connections` для сохранения API сервиса.
		"""

		return f"{self.id}-{name}"

	def save_connection(self, service_api: BaseTelehooperServiceAPI) -> None:
		"""
		Сохраняет ServiceAPI в объект пользователя.

		После сохранения в память, извлечь API можно через методы по типу `get_vk_connection`.
		"""

		_saved_connections[self._get_service_store_name(service_api.service_name)] = service_api

	def _get_connection(self, name: str) -> VKServiceAPI | None:
		"""
		Возвращает ServiceAPI из объекта пользователя.

		Если API не был сохранён, возвращается None.

		Рекомендуется использовать методы по типу `get_vk_connection`.
		"""

		return _saved_connections.get(self._get_service_store_name(name))

	def _remove_connection(self, name: str) -> None:
		"""
		Удаляет ServiceAPI из объекта пользователя.
		"""

		_saved_connections.pop(self._get_service_store_name(name), None)

	def get_vk_connection(self) -> VKServiceAPI | None:
		"""
		Возвращает ServiceAPI для ВКонтакте из объекта пользователя.

		Если API не был сохранён, возвращается None.
		"""

		return self._get_connection("VK")

	def remove_vk_connection(self) -> None:
		"""
		Удаляет ServiceAPI для ВКонтакте из объекта пользователя.
		"""

		self._remove_connection("VK")

	def has_role(self, role: str, allow_any: bool = True) -> bool:
		"""
		Проверяет, есть ли у пользователя роль `role`.

		:param role: Роль, которую нужно проверить.
		:param allow_any: Если `True`, то при наличии роли `*` у пользователя возвращается `True`.
		"""

		if allow_any and "*" in self.roles:
			return True

		return role.lower() in [i.lower() for i in self.roles]

	async def restrict_in_debug(self) -> None:
		"""
		Вызывает Exception, если включён debug-режим у бота, а пользователь не имеет роли "tester".
		"""

		await TelehooperAPI.restrict_in_debug(self)

	async def get_setting(self, path: str, force_refresh: bool = False) -> Any:
		"""
		Возвращает значение настройки по пути `path`.

		Вызывает исключение, если настройка не найдена.
		"""

		if force_refresh:
			await self.refresh_document()

		return self.settingsOverriden.get(path, settings.get_default_setting_value(path))

	async def save_setting(self, path: str, new_value: Any) -> None:
		"""
		Сохраняет настройку по пути `path` в БД. Если новое значение настройки не отличается от значения по-умолчанию, то бот не сохранит данную запись.

		Вызовет исключение, если настройка не существует.
		"""

		is_default = settings.get_default_setting_value(path) == new_value

		if is_default:
			self.rawDocument["SettingsOverriden"].pop(path, None)
			self.settingsOverriden = self.rawDocument["SettingsOverriden"]
			await self.rawDocument.save()

			return

		self.rawDocument["SettingsOverriden"].update({
			path: new_value
		})
		self.settingsOverriden = self.rawDocument["SettingsOverriden"]
		await self.rawDocument.save()

class TelehooperGroup:
	"""
	Класс с информацией о группе, которая связана с каким-либо сервисом.
	"""

	id: int
	creatorID: int
	createdAt: int
	lastActivityAt: int
	userJoinedWarning: bool
	statusMessageID: int
	adminRights: bool
	chats: dict
	services: dict

	rawDocument: Document
	telegramChat: Chat
	bot: Bot

	def __init__(self, rawDocument: Document, telegramChat: Chat, bot: Bot) -> None:
		self.rawDocument = rawDocument
		self.telegramChat = telegramChat
		self.bot = bot

		self.id = rawDocument["ID"]
		self.creatorID = rawDocument["Creator"]
		self.createdAt = rawDocument["CreatedAt"]
		self.lastActivityAt = rawDocument["LastActivityAt"]
		self.userJoinedWarning = rawDocument["UserJoinedWarning"]
		self.statusMessageID = rawDocument["StatusMessageID"]
		self.adminRights = rawDocument["AdminRights"]
		self.chats = rawDocument["Chats"]
		self.services = rawDocument["Services"]

	async def convert_to_dialogue_group(self, user: TelehooperUser, dialogue: ServiceDialogue, pinned_message: Message) -> None:
		"""
		Конвертирует данную Telegram-группу в группу-диалог из сервиса.

		Данный метод изменяет название, фотографию, закреп, а так же описание группы. Помимо этого, она сохраняет информацию о созданной группе в БД.
		"""

		async def _sleep():
			await asyncio.sleep(1.5)

		async def _longSleep():
			await asyncio.sleep(3.5)

		# Пытаемся изменить название группы.
		if dialogue.name:
			try:
				await self.telegramChat.set_title(dialogue.name)
			except:
				await _longSleep()
			else:
				await _sleep()

		# Пытаемся изменить фотографию группы.
		if dialogue.profile_img or dialogue.profile_url:
			picture_bytes = dialogue.profile_img
			if dialogue.profile_url:
				async with aiohttp.ClientSession() as session:
					async with session.get(dialogue.profile_url) as response:
						picture_bytes = await response.read()

			assert picture_bytes

			try:
				await self.telegramChat.set_photo(
					photo=BufferedInputFile(
						file=picture_bytes,
						filename="photo.png"
					)
				)
			except:
				await _longSleep()
			else:
				await _sleep()

		# Пытаемся поменять описание группы.
		try:
			await self.telegramChat.set_description(
				f"@telehooper_bot: Группа для диалога «{dialogue.name}» из ВКонтакте.\n"
				"\n"
				"ℹ️ Для управления данной группой используйте команду /this."
			)
		except:
			await _longSleep()
		else:
			await _sleep()

		# Редактируем текст сообщения.
		try:
			await pinned_message.edit_text(
				"<b>🫂 Группа-диалог ВКонтакте</b>.\n"
				"\n"
				"Используйте данное сообщения для выполнения быстрых действий над этой группой-диалогом.\n"
				"\n"
				"<i>WIP!</i>"
			)
		except:
			await _longSleep()
		else:
			await _sleep()

		# Пытаемся закрепить сообщение.
		try:
			await self.telegramChat.pin_message(
				pinned_message.message_id,
				disable_notification=True
			)
		except:
			await _longSleep()
		else:
			await _sleep()

		# Сохраняем в память.
		TelehooperAPI.save_subgroup(
			TelehooperSubGroup(
				id=pinned_message.message_thread_id or 0,
				service_id=dialogue.id,
				dialogue_name=dialogue.name,
				service=dialogue.service_name,
				parent=self
			)
		)

		# Делаем изменения в БД.
		# Сохраняем информацию о пользователе.
		if not self.id in user.rawDocument["Groups"]:
			user.rawDocument["Groups"].append(self.id)

			await user.rawDocument.save()

		# Сохраняем информацию в группе.
		self.rawDocument["LastActivityAt"] = utils.get_timestamp()
		self.rawDocument["Chats"].update({
			pinned_message.message_thread_id or 0: get_default_subgroup(
				topic_id=pinned_message.message_thread_id or 0,
				service_name=dialogue.service_name,
				dialogue_id=dialogue.id,
				dialogue_name=dialogue.name or "Без названия",
				pinned_message=pinned_message.message_id
			)
		})

		await self.rawDocument.save()

	async def send_message(self, text: str, topic: int = 0) -> None:
		"""
		Отправляет сообщение в группу.
		"""

		await self.bot.send_message(
			message_thread_id=topic,
			text=text,
			chat_id=self.id
		)

class TelehooperSubGroup:
	"""
	Класс для под-группы в группе-диалоге. Используется для всех диалогов внутри группы Telegram. Класс существует поскольку группы могут быть топиками с множеством диалогов.
	"""

	id: int
	service_id: int
	service_dialogue_name: str | None
	service_name: str
	parent: TelehooperGroup

	def __init__(self, id: int, service_id: int, dialogue_name: str | None, service: str, parent: TelehooperGroup) -> None:
		self.id = id
		self.service_id = service_id
		self.service_dialogue_name = dialogue_name
		self.service_name = service
		self.parent = parent

	async def send_message_in(self, text: str) -> None:
		"""
		Отправляет сообщение в Telegram-группу.
		"""

		await self.parent.send_message(text)

	async def send_message_out(self) -> None:
		"""
		Отправляет сообщение в сервис.
		"""

		pass

class TelehooperAPI:
	"""
	Класс с различными API бота Telehooper.
	"""

	@staticmethod
	async def get_user(user: User) -> TelehooperUser:
		"""
		Возвращает объект TelehooperUser.
		"""

		return TelehooperUser(
			await db_get_user(user),
			user
		)

	@staticmethod
	async def get_user_by_id(user_id: int) -> TelehooperUser | None:
		"""
		Возвращает объект TelehooperUser, либо None, если данного пользователя нет в БД, или же если он не писал боту.
		"""

		bot = Bot.get_current()
		if not bot:
			return

		try:
			user = (await (bot).get_chat_member(user_id, user_id)).user

			return TelehooperUser(
				await (await get_db())[f"user_{user_id}"],
				user
			)
		except:
			return None

	@staticmethod
	async def get_group(chat: Chat | int, db_group: Document | None = None) -> TelehooperGroup | None:
		"""
		Возвращает объект группы, либо None, если данной группы нет в БД, или же если бот не состоит в ней.
		"""

		chat_id = chat if isinstance(chat, int) else chat.id

		bot = Bot.get_current()
		assert bot

		return TelehooperGroup(
			db_group if db_group else await get_group(chat_id),
			chat if isinstance(chat, Chat) else (await bot.get_chat(chat_id)),
			bot
		)

	@staticmethod
	async def restrict_in_debug(user: TelehooperUser | User | None) -> None:
		"""
		Вызывает Exception, если включён debug-режим у бота, а пользователь не имеет роли "tester".
		"""

		_exc = DisallowedInDebugException("Вы не можете пользоваться данным функционалом бота при запущенном debug-режиме. Если Вы разработчик — обратитесь к консоли бота.")

		if not user:
			raise _exc

		if not config.debug:
			return

		if isinstance(user, User):
			user = await TelehooperAPI.get_user(user)


		if not user.has_role("tester"):
			raise _exc

	@staticmethod
	def save_subgroup(group: TelehooperSubGroup) -> None:
		"""
		Сохраняет TelehooperSubGroup в память бота с целью кэширования.
		"""

		_service_dialogues.append(group)

	@staticmethod
	def get_subgroup_by_service_dialogue(user: TelehooperUser, dialogue: ServiceDialogue) -> TelehooperSubGroup | None:
		"""
		Возвращает TelehooperSubGroup по диалогу из сервиса.

		Если группа не найдена, возвращается None.
		"""

		for servDialog in _service_dialogues:
			if servDialog.parent.creatorID != user.id:
				continue

			if servDialog.service_name != dialogue.service_name:
				continue

			if servDialog.service_id != dialogue.id:
				continue

			return servDialog

		return None

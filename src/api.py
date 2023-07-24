# coding: utf-8

import asyncio
import base64
from typing import Any, Sequence, cast

import aiohttp
from aiocouch import Document, NotFoundError
from aiogram import Bot
from aiogram.filters import Command
from aiogram.filters.command import CommandPatternType
from aiogram.types import Audio, BufferedInputFile, Chat
from aiogram.types import Document as TelegramDocument
from aiogram.types import (ForceReply, InlineKeyboardMarkup, InputFile,
                           InputMediaAudio, InputMediaDocument,
                           InputMediaPhoto, InputMediaVideo, Message,
                           PhotoSize, ReplyKeyboardMarkup, ReplyKeyboardRemove,
                           User, Video)
from magic_filter import MagicFilter

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
_cached_message_ids: list["TelehooperMessage"] = []
_cached_attachments: list["TelehooperCachedAttachment"] = []
_media_group_messages: dict[str, list] = {}

settings = SettingsHandler(SETTINGS_TREE)

class TelehooperUser:
	"""
	Пользователь бота Telehooper.
	"""

	creation_date: int
	"""UNIX-Время первого сообщения пользователя боту."""
	botBanned: bool
	"""Заблокировал ли пользователь бота?"""
	settingsOverriden: dict
	"""Словарь из настроек, которые были переопределены пользователем."""
	knownLanguage: str | None
	"""Язык, который известен боту."""
	roles: list[str]
	"""Роли пользователя."""
	connections: dict
	"""Список подключённых сервисов."""
	document: Document
	"""Документ пользователя в БД."""
	telegramUser: User
	"""Объект пользователя в Telegram."""

	def __init__(self, document: Document, user: User) -> None:
		"""
		Инициализирует объект пользователя.

		:param document: Документ пользователя в БД.
		:param user: Объект пользователя в Telegram.
		"""

		self.document = document
		self.telegramUser = user
		self._parse_document(document)

	def _parse_document(self, user: Document) -> None:
		"""
		Парсит значение документа пользователя в объект пользователя.

		:param user: Документ пользователя в БД.
		"""

		self.creation_date = user["CreationDate"]
		self.botBanned = user["BotBanned"]
		self.settingsOverriden = user["SettingsOverriden"]
		self.knownLanguage = user["KnownLanguage"]
		self.roles = user["Roles"]
		self.connections = user["Connections"]

	async def refresh_document(self) -> Document:
		"""
		Изменяет значения переменных данного класа, что бы соответствовать документу в БД.
		"""

		self.document = await db_get_user(self.telegramUser)
		self._parse_document(self.document)

		return self.document

	def _get_service_store_name(self, name: str) -> str:
		"""
		Возвращает название ключа в словаре `connections` для сохранения API сервиса.

		:param name: Название сервиса.
		"""

		return f"{self.telegramUser.id}-{name}"

	def save_connection(self, service_api: BaseTelehooperServiceAPI) -> None:
		"""
		Сохраняет ServiceAPI в объект пользователя. После сохранения в память, извлечь API можно через методы по типу `get_vk_connection`.

		:param service_api: ServiceAPI, который нужно сохранить.
		"""

		_saved_connections[self._get_service_store_name(service_api.service_name)] = service_api

	def _get_connection(self, name: str) -> BaseTelehooperServiceAPI | None:
		"""
		Возвращает ServiceAPI из объекта пользователя. Если API не был сохранён, возвращается None. Рекомендуется вместо этого использовать методы по типу `get_vk_connection`.

		:param name: Название сервиса.
		"""

		return _saved_connections.get(self._get_service_store_name(name))

	def _remove_connection(self, name: str) -> None:
		"""
		Удаляет ServiceAPI из объекта пользователя.

		:param name: Название сервиса.
		"""

		_saved_connections.pop(self._get_service_store_name(name), None)

	def get_vk_connection(self) -> VKServiceAPI | None:
		"""
		Возвращает ServiceAPI для ВКонтакте из объекта пользователя.

		Если API не был сохранён, возвращается None.
		"""

		return cast(VKServiceAPI, self._get_connection("VK"))

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
		Возвращает значение настройки по пути `path`. Вызывает исключение, если настройка не найдена.

		:param path: Путь к настройке.
		:param force_refresh: Обновить ли документ пользователя в БД перед получением настройки.
		"""

		if force_refresh:
			await self.refresh_document()

		return self.settingsOverriden.get(path, settings.get_default_setting_value(path))

	async def save_setting(self, path: str, new_value: Any) -> None:
		"""
		Сохраняет настройку по пути `path` в БД. Если новое значение настройки не отличается от значения по-умолчанию, то бот не сохранит данную запись. Вызовет исключение, если настройка не существует.

		:param path: Путь к настройке.
		:param new_value: Новое значение настройки.
		"""

		is_default = settings.get_default_setting_value(path) == new_value

		if is_default:
			self.document["SettingsOverriden"].pop(path, None)
			self.settingsOverriden = self.document["SettingsOverriden"]

			await self.document.save()

			return

		self.document["SettingsOverriden"].update({path: new_value})
		self.settingsOverriden = self.document["SettingsOverriden"]
		await self.document.save()

class TelehooperGroup:
	"""
	Класс с информацией о группе, которая связана с каким-либо сервисом.
	"""

	creatorID: int
	"""ID пользователя Telegram, который является создателем (администратором) данной группы."""
	createdAt: int
	"""UNIX-Время создания группы."""
	lastActivityAt: int
	"""UNIX-Время последней активности в группе."""
	userJoinedWarning: bool
	"""Указывает, отправлял ли бот предупреждение о том, что сторонний пользователь вступил в группу."""
	statusMessageID: int
	"""ID статусного сообщения, которое было закреплено в группе."""
	adminRights: bool
	"""Имеет ли бот права администратора в группе."""
	chats: dict
	"""Список диалогов в группе."""
	services: dict
	"""Информация, настройки сервисов в данной группе."""

	creator: TelehooperUser
	"""Создатель группы."""
	document: Document
	"""Документ группы в БД."""
	chat: Chat
	"""Объект группы в Telegram."""
	bot: Bot
	"""Объект бота в Telegram."""

	def __init__(self, creator: TelehooperUser, document: Document, chat: Chat, bot: Bot) -> None:
		"""
		Инициализирует объект группы.

		:param creator: Создатель группы.
		:param document: Документ группы в БД.
		:param chat: Объект группы в Telegram.
		:param bot: Объект бота в Telegram.
		"""

		self.document = document
		self.creator = creator
		self.chat = chat
		self.bot = bot

		self.creatorID = document["Creator"]
		self.createdAt = document["CreatedAt"]
		self.lastActivityAt = document["LastActivityAt"]
		self.userJoinedWarning = document["UserJoinedWarning"]
		self.statusMessageID = document["StatusMessageID"]
		self.adminRights = document["AdminRights"]
		self.chats = document["Chats"]
		self.services = document["Services"]

	async def convert_to_dialogue_group(self, user: TelehooperUser, dialogue: ServiceDialogue, pinned_message: Message, serviceAPI: BaseTelehooperServiceAPI) -> None:
		"""
		Конвертирует данную Telegram-группу в группу-диалог из сервиса. Данный метод изменяет название, фотографию, а так же описание группы. Помимо этого, она сохраняет информацию о созданной группе в БД.

		:param user: Пользователь, который создал группу-диалог.
		:param dialogue: Диалог, который нужно сохранить.
		:param pinned_message: Сообщение, которое используется как статусное.
		:param serviceAPI: API сервиса, который нужно использовать для отправки сообщений.
		"""

		async def _sleep():
			await asyncio.sleep(1)

		async def _longSleep():
			await asyncio.sleep(4)

		# Пытаемся изменить название группы.
		if dialogue.name:
			try:
				await self.chat.set_title(dialogue.name)
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
				await self.chat.set_photo(
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
			await self.chat.set_description(
				f"@{utils.get_bot_username()}: Группа для диалога «{dialogue.name}» из ВКонтакте.\n"
				"\n"
				"ℹ️ Для управления данной группой используйте команду /this."
			)
		except:
			await _longSleep()
		else:
			await _sleep()

		# Сохраняем в память.
		TelehooperAPI.save_subgroup(
			TelehooperSubGroup(
				id=pinned_message.message_thread_id or 0,
				dialogue_name=dialogue.name,
				service=serviceAPI,
				parent=self,
				service_chat_id=dialogue.id
			)
		)

		# Делаем изменения в БД.
		# Сохраняем информацию о пользователе.
		if not self.chat.id in user.document["Groups"]:
			user.document["Groups"].append(self.chat.id)

			await user.document.save()

		# Сохраняем информацию в группе.
		self.document["LastActivityAt"] = utils.get_timestamp()
		self.document["Chats"].update({
			pinned_message.message_thread_id or 0: get_default_subgroup(
				topic_id=pinned_message.message_thread_id or 0,
				service_name=dialogue.service_name,
				dialogue_id=dialogue.id,
				dialogue_name=dialogue.name or "Без названия",
				pinned_message=pinned_message.message_id
			)
		})

		await self.document.save()

	async def send_sticker(self, sticker: BufferedInputFile | InputFile | str, reply_to: int | None = None, topic: int = 0, silent: bool = False) -> list[Message]:
		"""
		Отправляет стикер в Telegram-группу.

		:param sticker: Стикер.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param silent: Отправить ли сообщение без уведомления.
		"""

		return [await self.bot.send_sticker(
			chat_id=self.chat.id,
			sticker=sticker,
			message_thread_id=topic,
			reply_to_message_id=reply_to,
			disable_notification=silent,
			allow_sending_without_reply=True
		)]

	async def send_geo(self, latitude: float, longitude: float, reply_to: int | None = None, topic: int = 0, silent: bool = False) -> list[Message]:
		"""
		Отправляет геолокацию в Telegram-группу.

		:param latitude: Широта.
		:param longitude: Долгота.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param silent: Отправить ли сообщение без уведомления.
		"""

		return [await self.bot.send_location(
			chat_id=self.chat.id,
			latitude=latitude,
			longitude=longitude,
			message_thread_id=topic,
			reply_to_message_id=reply_to,
			disable_notification=silent,
			allow_sending_without_reply=True
		)]

	async def send_message(self, text: str, attachments: list[InputMediaAudio | InputMediaDocument | InputMediaPhoto | InputMediaVideo] | None = None, reply_to: int | None = None, topic: int = 0, silent: bool = False) -> list[int]:
		"""
		Отправляет сообщение в группу. Возвращает ID отправленного(-ых) сообщений.

		:param text: Текст сообщения.
		:param attachments: Telegram-вложения.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param silent: Отправить ли сообщение без уведомления.
		"""

		if not attachments:
			attachments = []

		message_ids = []

		# В Telegram, при отправке медиа-группы, поле "caption" выступает как текст сообщения, отображаемое сверху сообщения.
		# По этой причине, тут мы меняем текст вложения на текст сообщения, которое мы пытаемся отправить.
		if attachments:
			attachments[0].caption = text

		if attachments:
			# У нас есть хотя бы одно вложение, отправляем как медиа-группу.

			message_ids = [i.message_id for i in await self.bot.send_media_group(
				chat_id=self.chat.id,
				media=attachments,
				message_thread_id=topic,
				reply_to_message_id=reply_to,
				disable_notification=silent,
				allow_sending_without_reply=True
			)]
		else:
			# Вложений нету.

			message_ids = [(await self.bot.send_message(
				chat_id=self.chat.id,
				message_thread_id=topic,
				reply_to_message_id=reply_to,
				text=text,
				disable_notification=silent,
				allow_sending_without_reply=True
			)).message_id]

		return message_ids

class TelehooperMessage:
	"""
	Класс, описывающий сообщение отправленного через Telehooper. Данный класс предоставляет доступ к ID сообщения в сервисе и в Telegram, а так же прочую информацию.
	"""

	service: str
	"""Название сервиса, через который было отправлено сообщение."""
	telegram_message_ids: list[int]
	"""Список ID сообщений в Telegram. Может быть несколько, если сообщение является альбомом."""
	service_message_ids: list[int]
	"""Список ID сообщений в сервисе. Может быть несколько, если сообщение является альбомом."""
	sent_via_bot: bool
	"""Отправлено ли сообщение через бота."""

	def __init__(self, service: str, telegram_mids: int | list[int], service_mids: int | list[int], sent_via_bot: bool = False) -> None:
		"""
		Инициализирует объект сообщения.

		:param service: Название сервиса, через который было отправлено сообщение.
		:param telegram_mids: ID сообщения(-ий) в Telegram.
		:param service_mids: ID сообщения(-ий) в сервисе.
		:param sent_via_bot: Отправлено ли сообщение через бота.
		"""

		self.service = service
		self.telegram_message_ids = [telegram_mids] if isinstance(telegram_mids, int) else telegram_mids
		self.service_message_ids = [service_mids] if isinstance(service_mids, int) else service_mids
		self.sent_via_bot = sent_via_bot

class TelehooperCachedAttachment:
	"""
	Класс, описывающий вложение, которое было сохранено в Telegram. Данный класс предоставляет доступ к ID вложения в Telegram и в сервисе, а так же прочую информацию.
	"""

	service_name: str
	"""Имя сервиса, с которым ассоциировано вложение."""
	key: str
	"""Ключ вложения в БД. Захеширован при помощи SHA-256."""
	value: str
	"""Значение вложения в БД. Зашифровано при помощи Fernet, ключ - `key` (до хэширования)."""

	def __init__(self, service_name: str, key: str, value: str) -> None:
		"""
		Инициализирует объект вложения.

		:param service_name: Имя сервиса, с которым ассоциировано вложение.
		:param key: Ключ вложения в БД. Захеширован при помощи SHA-256.
		:param value: Значение вложения в БД. Зашифровано при помощи Fernet, ключ - `key` (до хэширования).
		"""

		self.service_name = service_name
		self.key = key
		self.value = value

class TelehooperSubGroup:
	"""
	Класс для под-группы в группе-диалоге. Используется для всех диалогов внутри группы Telegram. Класс существует поскольку группы могут быть топиками с множеством диалогов.
	"""

	id: int
	"""ID топика Telegram. Может быть значением `0`, если это главная группа, которая не имеет топиков."""
	service_dialogue_name: str | None
	"""Название диалога в сервисе. В некоторых случаях может отсутствовать."""
	parent: TelehooperGroup
	"""Группа, являющаяся родителем данной суб-группы."""
	service: BaseTelehooperServiceAPI
	"""API сервиса."""
	service_chat_id: int
	"""ID диалога в сервисе."""

	def __init__(self, id: int, dialogue_name: str | None, service: BaseTelehooperServiceAPI, parent: TelehooperGroup, service_chat_id: int) -> None:
		"""
		Инициализирует объект суб-группы.

		:param id: ID топика Telegram. Может быть значением `0`, если это главная группа, которая не имеет топиков.
		:param dialogue_name: Название диалога в сервисе. В некоторых случаях может отсутствовать.
		:param service: API сервиса.
		:param parent: Группа, являющаяся родителем данной суб-группы.
		:param service_chat_id: ID диалога в сервисе.
		"""

		self.id = id
		self.service_dialogue_name = dialogue_name
		self.service = service
		self.parent = parent
		self.service_chat_id = service_chat_id

	async def send_sticker(self, sticker: BufferedInputFile | InputFile | str, reply_to: int | None = None, silent: bool = False) -> list[Message]:
		"""
		Отправляет стикер в Telegram-группу.

		:param sticker: Стикер.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param silent: Отправить ли сообщение без уведомления.
		"""

		return await self.parent.send_sticker(sticker, reply_to=reply_to, topic=self.id, silent=silent)

	async def send_geo(self, latitude: float, longitude: float, reply_to: int | None = None, silent: bool = False) -> list[Message]:
		"""
		Отправляет геолокацию в Telegram-группу.

		:param latitude: Широта.
		:param longitude: Долгота.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param silent: Отправить ли сообщение без уведомления.
		"""

		return await self.parent.send_geo(latitude, longitude, reply_to=reply_to, topic=self.id, silent=silent)

	async def send_message_in(self, text: str, attachments: list[InputMediaAudio | InputMediaDocument | InputMediaPhoto | InputMediaVideo] | None = None, reply_to: int | None = None, silent: bool = False) -> list[int]:
		"""
		Отправляет сообщение в Telegram-группу.

		:param text: Текст сообщения.
		:param attachments: URL-адреса вложений.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param silent: Отправить ли сообщение без уведомления.
		"""

		return await self.parent.send_message(text, attachments=attachments, topic=self.id, silent=silent, reply_to=reply_to)

	async def send_message_out(self, text: str) -> None:
		"""
		Отправляет сообщение в сервис.

		:param text: Текст сообщения.
		"""

		await self.service.send_message(chat_id=self.parent.chat.id, text=text)

	def __repr__(self) -> str:
		return f"<{self.service.service_name} TelehooperSubGroup for {self.service_dialogue_name}>"

class TelehooperAPI:
	"""
	Класс с различными API бота Telehooper.
	"""

	@staticmethod
	def get_settings() -> SettingsHandler:
		"""
		Возвращает объект SettingsHandler, который предоставляет доступ к настройкам бота.
		"""

		return settings

	@staticmethod
	async def get_user(user: User) -> TelehooperUser:
		"""
		Возвращает объект TelehooperUser.

		:param user: Объект пользователя в Telegram.
		"""

		return TelehooperUser(
			await db_get_user(user),
			user
		)

	@staticmethod
	async def get_user_by_id(user_id: int) -> TelehooperUser | None:
		"""
		Возвращает объект TelehooperUser, либо None, если данного пользователя нет в БД, или же если он не писал боту.

		:param user_id: ID пользователя в Telegram.
		"""

		bot = Bot.get_current()
		assert bot

		try:
			user = (await (bot).get_chat_member(user_id, user_id)).user

			return TelehooperUser(
				await (await get_db())[f"user_{user_id}"],
				user
			)
		except:
			return None

	@staticmethod
	async def get_group(user: TelehooperUser, chat: Chat | int, db_group: Document | None = None) -> TelehooperGroup | None:
		"""
		Возвращает объект группы, либо None, если данной группы нет в БД, или же если бот не состоит в ней.

		:param user: Пользователь, который создал (владеет) группой.
		:param chat: Объект группы в Telegram.
		:param db_group: Документ группы в БД. Если не указано, бот попытается получить его самостоятельно.
		"""

		chat_id = chat if isinstance(chat, int) else chat.id

		bot = Bot.get_current()
		assert bot

		try:
			return TelehooperGroup(
				user,
				db_group if db_group else await get_group(chat_id),
				chat if isinstance(chat, Chat) else (await bot.get_chat(chat_id)),
				bot
			)
		except NotFoundError:
			return None

	@staticmethod
	async def restrict_in_debug(user: TelehooperUser | User | None) -> None:
		"""
		Вызывает Exception, если включён debug-режим у бота, а пользователь не имеет роли "tester".

		:param user: Пользователь, которого нужно проверить. Если не указано, то бот мгновенно вызовет Exception при включённом debug-режиме.
		"""

		_exc = DisallowedInDebugException("Вы не можете пользоваться данным функционалом бота при запущенном debug-режиме. Если Вы разработчик — обратитесь к консоли бота")

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

		Используйте следующие методы для получения TelehooperSubGroup:
		- `get_subgroup_by_chat`.
		- `get_subgroup_by_service_dialogue`.

		:param group: TelehooperSubGroup, который нужно сохранить.
		"""

		_service_dialogues.append(group)

	@staticmethod
	def get_subgroup_by_service_dialogue(user: TelehooperUser, dialogue: ServiceDialogue) -> TelehooperSubGroup | None:
		"""
		Возвращает TelehooperSubGroup по диалогу из сервиса.

		Если группа не найдена, возвращается None.

		:param user: Пользователь, который создал (владеет) группой.
		:param dialogue: Диалог, который нужно найти.
		"""

		for servDialog in _service_dialogues:
			if servDialog.parent.creatorID != user.telegramUser.id:
				continue

			if servDialog.service.service_name != dialogue.service_name:
				continue

			if servDialog.service_chat_id != dialogue.id:
				continue

			return servDialog

		return None

	@staticmethod
	def get_subgroup_by_chat(group: TelehooperGroup, topic_id: int = 0) -> TelehooperSubGroup | None:
		"""
		Возвращает TelehooperSubGroup по чату Telegram.

		Если группа не найдена, возвращается None.

		:param group: Telegram-группа, в которой нужно найти диалог.
		:param topic_id: ID топика Telegram. Если не указано, то возвращается главная группа.
		"""

		for servDialog in _service_dialogues:
			if servDialog.parent.creatorID != group.creatorID:
				continue

			if servDialog.parent.chat.id != group.chat.id:
				continue

			if servDialog.id != topic_id:
				continue

			return servDialog

		return None

	@staticmethod
	async def save_message(service_name: str, telegram_message_id: int | list[int], service_message_id: int | list[int], sent_via_bot: bool = True):
		"""
		Сохраняет ID отправленного сообщения в БД.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param telegram_message_id: ID сообщения(-ий) в Telegram.
		:param service_message_id: ID сообщения(-ий) в сервисе.
		:param sent_via_bot: Отправлено ли сообщение через бота.
		"""

		msg = TelehooperMessage(
			service=service_name,
			telegram_mids=telegram_message_id,
			service_mids=service_message_id,
			sent_via_bot=sent_via_bot
		)

		_cached_message_ids.append(msg)

		# TODO: Сохранить в БД.

	@staticmethod
	async def delete_message(service_name: str, telegram_message_id: int | list[int] | None = None, service_message_id: int | list[int] | None = None):
		"""
		Удаляет ID сообщения из БД с соответствием по ID сообщения сервиса или Telegram.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param telegram_message_id: ID сообщения(-ий) в Telegram.
		:param service_message_id: ID сообщения(-ий) в сервисе.
		"""

		assert telegram_message_id or service_message_id, "Не указаны ID сообщений"

		if isinstance(telegram_message_id, int):
			telegram_message_id = [telegram_message_id]

		if isinstance(service_message_id, int):
			service_message_id = [service_message_id]

		telegram_message_id = cast(list[int], telegram_message_id)
		service_message_id = cast(list[int], service_message_id)

		for index, msg in enumerate(_cached_message_ids):
			if msg.service != service_name:
				continue

			for mid in telegram_message_id:
				if mid in msg.telegram_message_ids:
					continue

				del _cached_message_ids[index]

				return

			for mid in service_message_id:
				if mid in msg.service_message_ids:
					continue

				del _cached_message_ids[index]

				return

		# TODO: Удалить из БД.

	@staticmethod
	async def get_message_by_telegram_id(service_name: str, message_id: int, bypass_cache: bool = False) -> TelehooperMessage | None:
		"""
		Возвращает информацию о отправленном через бота сообщения по его ID в Telegram.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param message_id: ID сообщения в Telegram.
		:param bypass_cache: Игнорировать ли кэш. Если да, то бот будет искать сообщение только в БД.
		"""

		# Если нам это разрешено, возвращаем ID сообщения из кэша.
		if not bypass_cache:
			for msg in _cached_message_ids:
				if msg.service != service_name:
					continue

				if message_id in msg.telegram_message_ids:
					return msg

		# TODO: Извлечь информацию о сообщении из БД.

		return None

	@staticmethod
	async def get_message_by_service_id(service_name: str, message_id: int, bypass_cache: bool = False) -> TelehooperMessage | None:
		"""
		Возвращает информацию о отправленном через бота сообщения по его ID в сервисе.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param message_id: ID сообщения в сервисе.
		:param bypass_cache: Игнорировать ли кэш. Если да, то бот будет искать сообщение только в БД.
		"""

		# Если нам это разрешено, возвращаем ID сообщения из кэша.
		if not bypass_cache:
			for msg in _cached_message_ids:
				if msg.service != service_name:
					continue

				if message_id in msg.service_message_ids:
					return msg

		# TODO: Извлечь информацию о сообщении из БД.

		return None

	@staticmethod
	async def save_attachment(service_name: str, key: str, value: str):
		"""
		Сохраняет вложение с уникальным ID в БД с целью кэширования. Применяется для стикеров и GIF-анимаций.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param key: Уникальный ключ вложения. Данный ключ не должен быть хэширован.
		:param value: ID вложения в Telegram (поле `file_id` у сообщения). Данное значение не должно быть зашифрованым.
		"""

		attachment = TelehooperCachedAttachment(
			service_name=service_name,
			key=utils.sha256_hash(key),
			value=utils.encrypt_with_key(value, key)
		)

		_cached_attachments.append(attachment)

		# TODO: Сохранить в БД.

	@staticmethod
	async def get_attachment(service_name: str, key: str, bypass_cache: bool = False) -> str | None:
		"""
		Возвращает значение вложения по его уникальному ключу.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param key: Уникальный ключ вложения. Не должен быть хэширован.
		:param bypass_cache: Игнорировать ли кэш. Если да, то бот будет искать вложение только в БД.
		"""

		# Если нам это разрешено, возвращаем ID сообщения из кэша.
		if not bypass_cache:
			for attachment in _cached_attachments:
				if attachment.service_name != service_name:
					continue

				if attachment.key == utils.sha256_hash(key):
					return utils.decrypt_with_key(attachment.value, key)

		# TODO: Извлечь информацию о вложении из БД.

		return None

	@staticmethod
	async def send_or_edit_message(text: str, chat_id: int, message_to_edit: Message | int | None, thread_id: int | None = None, reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply | None = None, disable_web_page_preview: bool = False, allow_sending_without_reply: bool = False, bot: Bot | None = None) -> Message | int:
		"""
		Пытается отредактировать либо отправить сообщение в группу. Возвращает объект сообщения.
		"""

		message_id = message_to_edit.message_id if isinstance(message_to_edit, Message) else message_to_edit

		bot = bot if bot else Bot.get_current()
		assert bot

		async def _send() -> Message:
			return await bot.send_message(
				chat_id=chat_id,
				message_thread_id=thread_id,
				text=text,
				allow_sending_without_reply=allow_sending_without_reply,
				disable_web_page_preview=disable_web_page_preview,
				reply_markup=reply_markup
			)

		# Если не задан ID сообщения, то отправляем новое.
		if not message_id:
			return await _send()

		assert message_id

		# Пытаемся отредактировать сообщение, если не удаётся - отправляем новое.
		try:
			assert isinstance(reply_markup, InlineKeyboardMarkup)

			await bot.edit_message_text(
				chat_id=chat_id,
				message_id=message_id,
				text=text,
				reply_markup=reply_markup,
				disable_web_page_preview=disable_web_page_preview
			)

			return message_id
		except:
			return await _send()

async def get_subgroup(msg: Message) -> dict | None:
	"""
	Фильтр для входящих сообщений в группе. Если данная группа является диалог-группой, то данный метод вернёт объект TelehooperSubGroup.

	:param msg: Объект сообщения в Telegram.
	"""

	# Понятия не имею как, но бот получал свои же сообщения в данном хэндлере.
	if msg.from_user and msg.from_user.is_bot:
		return None

	telehooper_user = await TelehooperAPI.get_user(cast(User, msg.from_user))
	telehooper_group = await TelehooperAPI.get_group(telehooper_user, msg.chat)

	if not telehooper_group:
		return None

	telehooper_group = cast(TelehooperGroup, telehooper_group)

	topic_id = msg.message_thread_id or 0

	# Telegram в msg.message_thread_id возвращает ID сообщения, на которое был ответ.
	# Это ломает всего бота, поэтому нам приходится костылить.
	if not msg.is_topic_message:
		topic_id = 0

	subgroup = TelehooperAPI.get_subgroup_by_chat(telehooper_group, topic_id)

	if not subgroup:
		return None

	return {"subgroup": subgroup, "user": telehooper_user}

async def get_mediagroup(msg: Message) -> dict | None:
	"""
	Заставляет Handler дождаться получения всех сообщений из которых состоит медиа-группа, собирая все вложения в один список.

	:param msg: Объект сообщения в Telegram.
	"""

	def get_content(msg: Message) -> PhotoSize | Video | Audio | TelegramDocument | None:
		"""
		Извлекает медиа-контент из сообщения.

		:param message: Сообщение, из которого нужно извлечь медиа-контент.
		"""

		if msg.photo:
			return msg.photo[-1]

		if msg.video:
			return msg.video

		if msg.audio:
			return msg.audio

		if msg.document:
			return msg.document

		return None

	if not msg.media_group_id:
		return {"mediagroup": [get_content(msg)]}

	media_id = msg.media_group_id

	# Если уже существует медиагруппа с таким ключом, то просто добавляем сообщение в кэш медиагруппы.
	if media_id in _media_group_messages:
		_media_group_messages[media_id].append(msg)

		return None

	# Если медиагруппы с таким ключом нет, то создаём её.
	_media_group_messages[media_id] = [msg]


	await asyncio.sleep(0.5)

	return {"mediagroup": [get_content(i) for i in _media_group_messages.pop(media_id)]}

class CommandWithDeepLink(Command):
	"""
	Фильтр для Handler'ов, который позволяет обрабатывать команды из deep-link'ов.
	"""

	def __init__(self, *values: CommandPatternType, commands: CommandPatternType | Sequence[CommandPatternType] | None = None, prefix: str = "/", ignore_case: bool = False, ignore_mention: bool = False, magic: MagicFilter | None = None):
		super().__init__(*values, commands=commands, prefix=prefix, ignore_case=ignore_case, ignore_mention=ignore_mention, magic=magic)

	async def __call__(self, message: Message, bot: Bot) -> dict | bool:
		"""
		Вызывается при каждом входящем сообщении.
		"""

		def deeplink_command() -> dict | bool:
			text = message.text or message.caption
			if not text:
				return False

			command = self.extract_command(text)

			if not command or command.command != "start":
				return False

			if not command.args:
				return False

			try:
				command_extracted = self.extract_command("/" + base64.b64decode(command.args).decode())
			except:
				return False

			if command_extracted.command not in self.commands:
				return False

			return {"command": command_extracted}

		return (await super().__call__(message, bot)) or deeplink_command()

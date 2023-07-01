# coding: utf-8

from aiocouch import Document
from aiogram import Bot
from aiogram.types import Chat, User

from DB import get_db, get_group
from DB import get_user as db_get_user
from services.service_api_base import BaseTelehooperServiceAPI
from services.vk.service import VKServiceAPI


# Да, я знаю что это плохой способ. Знаю. Ни к чему другому, адекватному я не пришёл.
_saved_connections = {}

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
	connections: dict

	rawDocument: Document
	telegramUser: User

	def __init__(self, rawDocument: Document, telegramUser: User) -> None:
		self.rawDocument = rawDocument
		self.telegramUser = telegramUser

		self.id = rawDocument["ID"]
		self.username = rawDocument["Username"]
		self.name = rawDocument["Name"]
		self.creationDate = rawDocument["CreationDate"]
		self.botBanned = rawDocument["BotBanned"]
		self.settingsOverriden = rawDocument["SettingsOverriden"]
		self.connections = rawDocument["Connections"]

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

	def get_vk_connection(self) -> VKServiceAPI | None:
		"""
		Возвращает ServiceAPI для ВКонтакте из объекта пользователя.

		Если API не был сохранён, возвращается None.
		"""

		return self._get_connection("VK")

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

	def __init__(self, rawDocument: Document, telegramChat: Chat) -> None:
		self.rawDocument = rawDocument
		self.telegramChat = telegramChat

		self.id = rawDocument["ID"]
		self.creatorID = rawDocument["Creator"]
		self.createdAt = rawDocument["CreatedAt"]
		self.lastActivityAt = rawDocument["LastActivityAt"]
		self.userJoinedWarning = rawDocument["UserJoinedWarning"]
		self.statusMessageID = rawDocument["StatusMessageID"]
		self.adminRights = rawDocument["AdminRights"]
		self.chats = rawDocument["Chats"]
		self.services = rawDocument["Services"]

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
	async def get_group(chat: Chat | int) -> TelehooperGroup | None:
		"""
		Возвращает объект группы, либо None, если данной группы нет в БД, или же если бот не состоит в ней.
		"""

		chat_id = chat if isinstance(chat, int) else chat.id

		bot = Bot.get_current()
		if not bot:
			return

		return TelehooperGroup(
			await get_group(chat_id),
			chat if isinstance(chat, Chat) else (await (bot).get_chat(chat_id))
		)

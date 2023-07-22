# coding: utf-8

import enum
from typing import TYPE_CHECKING, Optional

from aiogram.types import Message

if TYPE_CHECKING:
	from api import TelehooperMessage, TelehooperSubGroup, TelehooperUser


class ServiceDialogue:
	"""
	Класс, обозначающий диалог из сервиса.

	В данном классе передана базовая информация, по типу ID диалога в сервисе, аватарка, название и подобное.
	"""

	id: int
	"""ID диалога в сервисе."""
	name: str | None
	"""Название диалога."""
	profile_url: str | None
	"""Ссылка на профиль диалога."""
	profile_img: bytes | None
	"""Аватарка диалога в виде байтов."""
	is_multiuser: bool
	"""Является ли диалог групповым (т.е., беседой)."""
	is_pinned: bool
	"""Закреплён ли диалог."""
	is_muted: bool
	"""Заглушен ли диалог."""
	service_name: str
	"""Название сервиса, из которого получен диалог."""

	def __init__(self, service_name: str, id: int, name: str | None = None, profile_url: str | None = None, profile_img: bytes | None = None, is_multiuser: bool = False, is_pinned: bool = False, is_muted: bool = False) -> None:
		self.service_name = service_name
		self.id = id
		self.name = name
		self.profile_url = profile_url
		self.profile_img = profile_img
		self.is_multiuser = is_multiuser
		self.is_pinned = is_pinned
		self.is_muted = is_muted

class ServiceDisconnectReason(enum.Enum):
	"""
	Причина отключения сервиса от Telehooper.
	"""

	INITIATED_BY_USER = "by-user"
	"""Отключение сервиса от бота было инициировано пользователем, воспользовавшись функционалом бота."""
	EXTERNAL = "external"
	"""Сервис был отключён внешними силами, например, владельцем аккаунта путём отзыва токена."""
	ERRORED = "errored"
	"""Сервис был отключён из-за ошибки, возникшей во время работы с ним."""
	ISSUED_BY_ADMIN = "by-admin"
	"""Сервис был отключён администратором бота."""
	TOKEN_NOT_STORED = "no-token"
	"""Сервис был отключён, так как у пользователя не был сохранён токен (настройка `Security.StoreTokens`)."""

class TelehooperServiceUserInfo:
	"""
	Класс с информацией о пользователе сервиса в Telehooper.
	"""

	service_name: str
	"""Название сервиса."""
	id: int
	"""ID пользователя в сервисе."""
	name: str
	"""Имя пользователя в сервисе."""
	profile_url: str | None
	"""Ссылка на профиль пользователя в сервисе."""
	profile_img: bytes | None
	"""Аватарка пользователя в виде байтов."""

	def __init__(self, service_name: str, id: int, name: str, profile_url: str | None = None, profile_img: bytes | None = None) -> None:
		self.service_name = service_name
		self.id = id
		self.name = name
		self.profile_url = profile_url
		self.profile_img = profile_img

class BaseTelehooperServiceAPI:
	"""
	Базовый API для сервисов Telehooper.
	"""

	user: "TelehooperUser"
	"""Пользователь, которому принадлежит данный сервис."""
	service_name: str
	"""Название сервиса."""
	service_user_id: int
	"""ID пользователя в сервисе."""

	def __init__(self, service_name: str, service_id: int, user: "TelehooperUser") -> None:
		"""
		Инициализирует данный Service API.

		:param service_name: Название сервиса.
		:param service_id: ID пользователя в сервисе.
		:param user: Пользователь, которому принадлежит данный сервис.
		"""

		self.service_name = service_name
		self.service_user_id = service_id
		self.user = user

	async def start_listening(self) -> None:
		"""
		Запускает прослушивание событий с сервиса, т.е., получение сообщений.

		Данный метод обязан создавать и возвращать `asyncio.Task`, не останавливая обработку основного loop'а.
		"""

		raise NotImplementedError

	async def get_list_of_dialogues(self, force_update: bool = False) -> list[ServiceDialogue]:
		"""
		Возвращает список диалогов из сервиса. Если список диалогов уже был получен, то он будет возвращён из кэша.

		:param force_update: Нужно ли обновить список диалогов, если он уже был получен ранее.
		"""

		raise NotImplementedError

	def has_cached_list_of_dialogues(self) -> bool:
		"""
		Возвращает, есть ли в кэше список диалогов.
		"""

		raise NotImplementedError

	async def disconnect_service(self, reason: ServiceDisconnectReason) -> None:
		"""
		Отключает сервис от Telehooper.

		:param reason: Причина отключения.
		"""

		raise NotImplementedError

	async def current_user_info(self) -> TelehooperServiceUserInfo:
		"""
		Возвращает информацию о текущем подключённом пользователе сервиса.
		"""

		raise NotImplementedError

	async def get_dialogue(self, chat_id: int, force_update: bool = False) -> ServiceDialogue:
		"""
		Возвращает диалог по его ID.

		Если диалог не был найден, то будет вызвана ошибка TypeError.

		:param chat_id: ID диалога.
		:param force_update: Нужно ли обновить данные о диалоге, если они уже были получены ранее.
		"""

		raise NotImplementedError

	async def send_message(self, chat_id: int, text: str, reply_to_message: int | None = None) -> None:
		"""
		Отправляет сообщение в диалог.

		:param chat_id: ID диалога.
		:param text: Текст сообщения.
		:param reply_to_message: ID сообщения, на которое нужно ответить.
		"""

		raise NotImplementedError

	async def handle_inner_message(self, msg: Message, subgroup: "TelehooperSubGroup", attachments: list) -> None:
		"""
		Метод, вызываемый ботом, в случае получения нового сообщения в группе-диалоге (или топик-диалоге). Этот метод обрабатывает события, передавая их текст в сервис.

		:param msg: Сообщение из Telegram. Если бот получил сразу кучу сообщений за раз (т.е., медиагруппу), то данная переменная будет равна первому сообщения из медиагруппы.
		:param subgroup: Подгруппа, в которой было получено сообщение.
		:param attachments: Вложения к сообщению.
		"""

		raise NotImplementedError

	async def handle_message_delete(self, msg: Message, subgroup: "TelehooperSubGroup") -> None:
		"""
		Метод, вызываемый ботом, в случае попытки удаления сообщения в группе-диалоге (или топик-диалоге) в боте при помощи команды `/delete`.

		:param msg: Сообщение из Telegram, которое должно быть удалено. Должно являться ответом (reply) на сообщение вместо сообщения с командой.
		:param subgroup: Подгруппа, в которой было получено сообщение.
		"""

		raise NotImplementedError

	async def handle_message_edit(self, msg: Message, subgroup: "TelehooperSubGroup") -> None:
		"""
		Метод, вызываемый ботом, в случае попытки редактирования сообщения в группе-диалоге (или топик-диалоге).

		:param msg: Новое сообщение из Telegram.
		:param subgroup: Подгруппа, в которой сообщение было отредактировано пользователем.
		"""

		raise NotImplementedError

	async def handle_message_read(self, subgroup: "TelehooperSubGroup") -> None:
		"""
		Метод, вызываемый ботом, в случае прочтения сообщения в группе-диалоге (или топик-диалоге) в боте при помощи команды `/read` либо нажатия кнопки "прочитать".

		:param subgroup: Подгруппа, в которой сообщение было прочитано.
		"""

		raise NotImplementedError

	async def handle_callback_button(self, msg: Message, subgroup: "TelehooperSubGroup") -> None:
		"""
		Метод, вызываемый ботом при нажатии на кнопку в сообщении в группе-диалоге (или топик-диалоге). Данный метод вызывается только при нажатии на кнопки, которые были скопированы с сервиса.

		:param msg: Сообщение из Telegram.
		:param subgroup: Подгруппа, в которой сообщение было прочитано.
		"""

		raise NotImplementedError

	async def get_message_by_telegram_id(self, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		"""
		Возвращает информацию о отправленном через бота сообщения по его ID в Telegram.

		:param message_id: ID сообщения в Telegram.
		:param bypass_cache: Игнорировать ли кэш. Если да, то бот будет искать сообщение только в БД.
		"""

		raise NotImplementedError

	async def get_message_by_service_id(self, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		"""
		Возвращает информацию о отправленном через бота сообщения по его ID в сервисе.

		:param message_id: ID сообщения в сервисе.
		:param bypass_cache: Игнорировать ли кэш. Если да, то бот будет искать сообщение только в БД.
		"""

		raise NotImplementedError

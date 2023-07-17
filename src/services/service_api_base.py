# coding: utf-8

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from api import TelehooperUser


class ServiceDialogue:
	"""
	Класс, обозначающий диалог из сервиса.

	В данном классе передана базовая информация, по типу ID диалога в сервисе, аватарка, название и подобное.
	"""

	id: int
	name: str | None
	profile_url: str | None
	profile_img: bytes | None
	is_multiuser: bool
	is_pinned: bool
	is_muted: bool
	service_name: str

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
	EXTERNAL = "external"
	ERRORED = "errored"
	ISSUED_BY_ADMIN = "by-admin"
	TOKEN_NOT_STORED = "no-token"

class TelehooperServiceUserInfo:
	"""
	Класс с информацией о пользователе сервиса в Telehooper.
	"""

	service_name: str
	id: int
	name: str
	profile_url: str | None
	profile_img: bytes | None

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
	service_name: str
	service_user_id: int

	def __init__(self, service_name: str, service_id: int, user: "TelehooperUser") -> None:
		"""
		Инициализирует данный Service API.

		:param service_name: Название сервиса.
		:param service_id: ID пользователя в сервисе.
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

# coding: utf-8

class ServiceDialogue:
	"""
	Класс, обозначающий диалог из сервиса.

	В данном классе передана базовая информация, по типу ID диалога в сервисе, аватарка, название и подобное.
	"""

	id: int
	name: str
	profile_url: str | None
	profile_img: bytes | None
	is_multiuser: bool
	is_pinned: bool
	is_muted: bool

	def __init__(self, id: int, name: str, profile_url: str | None = None, profile_img: bytes | None = None, is_multiuser: bool = False, is_pinned: bool = False, is_muted: bool = False) -> None:
		self.id = id
		self.name = name
		self.profile_url = profile_url
		self.profile_img = profile_img
		self.is_multiuser = is_multiuser
		self.is_pinned = is_pinned
		self.is_muted = is_muted

class BaseTelehooperServiceAPI:
	"""
	Базовый API для сервисов Telehooper.
	"""

	service_name: str
	service_user_id: int

	def __init__(self, service_name: str, service_id: int) -> None:
		"""
		Инициализирует данный Service API.

		:param service_name: Название сервиса.
		:param service_id: ID пользователя в сервисе.
		"""

		self.service_name = service_name
		self.service_user_id = service_id

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

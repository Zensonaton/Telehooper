# coding: utf-8

from __future__ import annotations

import asyncio
import enum
from typing import TYPE_CHECKING, Literal, Optional

from aiogram import Bot
from aiogram.types import (Audio, CallbackQuery, Document, Message,
                           MessageReactionUpdated, PhotoSize, Video, VideoNote)
from pyrate_limiter import BucketFullException, Limiter, RequestRate

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
	incoming_messages: int | None
	"""Количество входящих сообщений в диалоге. Может отсутствовать."""
	multiuser_count: int | None
	"""Количество участников в групповом диалоге. Может отсутствовать."""

	def __init__(self, service_name: str, id: int, name: str | None = None, profile_url: str | None = None, profile_img: bytes | None = None, is_multiuser: bool = False, is_pinned: bool = False, is_muted: bool = False, incoming_messages: int | None = None, multiuser_count: int | None = None) -> None:
		self.service_name = service_name
		self.id = id
		self.name = name
		self.profile_url = profile_url
		self.profile_img = profile_img
		self.is_multiuser = is_multiuser
		self.is_pinned = is_pinned
		self.is_muted = is_muted
		self.incoming_messages = incoming_messages
		self.multiuser_count = multiuser_count

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
	male: bool | None
	"""Пол пользователя. Может отсутствовать."""
	username: str | None
	"""@username/domain пользователя. Может отсутствовать."""

	def __init__(self, service_name: str, id: int, name: str, profile_url: str | None = None, profile_img: bytes | None = None, male: bool | None = None, username: str | None = None) -> None:
		self.service_name = service_name
		self.id = id
		self.name = name
		self.profile_url = profile_url
		self.profile_img = profile_img
		self.male = male
		self.username = username

class BaseTelehooperServiceAPI:
	"""
	Базовый API для сервисов Telehooper. Service API всегда привязан к одному пользователю, и может работать только с его аккаунтом.
	"""

	user: "TelehooperUser"
	"""Пользователь, которому принадлежит данный сервис."""
	service_name: str
	"""Название сервиса."""
	service_user_id: int
	"""ID пользователя в сервисе."""
	limiter: Limiter
	"""Лимитер для этого сервиса."""

	def __init__(self, service_name: str, service_id: int, user: "TelehooperUser", limiter: Limiter = Limiter(RequestRate(1, 1), RequestRate(20, 60))) -> None:
		"""
		Инициализирует данный Service API.

		:param service_name: Название сервиса.
		:param service_id: ID пользователя в сервисе.
		:param user: Пользователь, которому принадлежит данный сервис.
		:param limiter: Лимитер для этого сервиса.
		"""

		self.service_name = service_name
		self.service_user_id = service_id
		self.user = user
		self.limiter = limiter

	async def acquire_queue(self, key: str, max_delay: int | float | None = None) -> bool:
		"""
		Пытается получить место в очереди. Если место не было получено, то бот будет спать до тех пор, пока не получит место. Возвращает `True`, если место было получено, иначе `False`, если места вообще нет.

		:param key: Ключ, по которому нужно получить место в очереди.
		:param max_delay: Максимальное время ожидания в секундах. Если ожидание превысит это время, то метод вернёт `False`.
		"""

		while True:
			try:
				self.limiter.try_acquire(key)
			except BucketFullException as err:
				delay_time = float(err.meta_info["remaining_time"])

				exceeded_max_delay = max_delay and delay_time > max_delay
				if exceeded_max_delay:
					return False

				await asyncio.sleep(delay_time)
			else:
				return True

	def get_bucket_size(self, key: str) -> int:
		"""
		Возвращает 'заполненность' очереди по заданному имени.

		:param key: Ключ, по которому нужно получить заполненность очереди.
		"""

		try:
			return self.limiter.get_current_volume(key)
		except:
			return 0

	async def start_listening(self, bot: Bot | None = None) -> None:
		"""
		Запускает прослушивание событий с сервиса, т.е., получение сообщений.

		Данный метод обязан создавать и возвращать `asyncio.Task`, не останавливая обработку основного loop'а.

		:param bot: Объект бота, который используется для рассылки сообщений о ошибке подключения к сервису. Можно не указывать, и в таком случае рассылки не будет.
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

	async def get_current_user_info(self) -> TelehooperServiceUserInfo:
		"""
		Возвращает информацию о текущем подключённом пользователе сервиса.
		"""

		raise NotImplementedError

	async def get_service_dialogue(self, chat_id: int, force_update: bool = False) -> ServiceDialogue:
		"""
		Возвращает диалог по его ID.

		Если диалог не был найден, то будет вызвана ошибка TypeError.

		:param chat_id: ID диалога.
		:param force_update: Нужно ли обновить данные о диалоге, если они уже были получены ранее.
		"""

		raise NotImplementedError

	async def set_online(self) -> None:
		"""
		Устанавливает режим "онлайн" текущего пользователя.
		"""

		raise NotImplementedError

	async def start_chat_activity(self, peer_id: int, type: Literal["typing", "audiomessage"]) -> None:
		"""
		Вызывает событие "печатает" текущего пользователя в указанном диалоге.

		:param peer_id: ID диалога.
		:param type: Тип активности. Может быть либо `typing`, либо `audiomessage`.
		"""

		raise NotImplementedError

	async def read_message(self, peer_id: int) -> None:
		"""
		Помечает сообщения в указанном диалоге как прочитанные.

		:param peer_id: ID диалога.
		"""

		raise NotImplementedError

	async def send_callback(self, message_id: int, peer_id: int, data: str) -> None:
		"""
		Отправляет Callback query событие при нажатии на кнопку.

		:param message_id: ID сообщения, на котором была нажата кнопка.
		:param peer_id: ID диалога.
		:param data: Callback-данные.
		"""

		raise NotImplementedError

	async def send_message(self, chat_id: int, text: str, reply_to_message: int | None = None, attachments: list[str] | str | None = None, latitude: float | None = None, longitude: float | None = None, bypass_queue: bool = False) -> None:
		"""
		Отправляет сообщение в диалог.

		:param chat_id: ID диалога.
		:param text: Текст сообщения.
		:param reply_to_message: ID сообщения, на которое нужно ответить.
		:param attachments: Вложения к сообщению. Может быть как строкой, так и списком строк.
		:param latitude: Широта для геолокации.
		:param longitude: Долгота для геолокации.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		raise NotImplementedError

	async def set_reactions(self, chat_id: int, message_id: int, reactions: str | list[str], bypass_queue: bool = False) -> None:
		"""
		Устанавливает реакции под указанным сообщением.

		:param chat_id: ID диалога.
		:param reply_to_message: ID сообщения, на которое должно быть удалено/установлена реакция.
		:param reactions: Реакция или массив реакций, которые будут переключены у сообщения. Должны передаваться эмодзи реакций.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		raise NotImplementedError

	async def delete_reactions(self, chat_id: int, message_id: int, reactions: str | list[str], bypass_queue: bool = False) -> None:
		"""
		Удаляет реакции под указанным сообщением.

		:param chat_id: ID диалога.
		:param reply_to_message: ID сообщения, на которое должно быть удалено/установлена реакция.
		:param reactions: Реакция или массив реакций, которые будут переключены у сообщения. Должны передаваться эмодзи реакций.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		raise NotImplementedError

	async def handle_telegram_message(self, msg: Message, subgroup: "TelehooperSubGroup", user: "TelehooperUser", attachments: list[PhotoSize | Video | Audio | Document | VideoNote]) -> None:
		"""
		Метод, вызываемый ботом, в случае получения нового сообщения в группе-диалоге (или топик-диалоге). Этот метод обрабатывает события, передавая их текст в сервис.

		:param msg: Сообщение из Telegram. Если бот получил сразу кучу сообщений за раз (т.е., медиагруппу), то данная переменная будет равна первому сообщения из медиагруппы.
		:param subgroup: Подгруппа, в которой было получено сообщение.
		:param user: Пользователь, который отправил сообщение.
		:param attachments: Вложения к сообщению.
		"""

		raise NotImplementedError

	async def handle_telegram_message_delete(self, msg: Message, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		"""
		Метод, вызываемый ботом, в случае попытки удаления сообщения в группе-диалоге (или топик-диалоге) в боте при помощи команды `/delete`.

		:param msg: Сообщение из Telegram, которое должно быть удалено. Должно являться ответом (reply) на сообщение вместо сообщения с командой.
		:param subgroup: Подгруппа, в которой было получено сообщение.
		:param user: Пользователь, который отправил сообщение.
		"""

		raise NotImplementedError

	async def handle_telegram_message_edit(self, msg: Message, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		"""
		Метод, вызываемый ботом, в случае попытки редактирования сообщения в группе-диалоге (или топик-диалоге).

		:param msg: Новое сообщение из Telegram.
		:param subgroup: Подгруппа, в которой сообщение было отредактировано пользователем.
		:param user: Пользователь, который отредактировал сообщение.
		"""

		raise NotImplementedError

	async def handle_telegram_message_reaction(self, msg: MessageReactionUpdated, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		"""
		Метод, вызываемый ботом, в случае изменения реакций под сообщением в Telegram внутри группе-диалоге (или топик-диалоге).

		:param msg: Объект псевдосообщения, хранимый в себе информацию о том, какие реакции были ранее и теперь присутствуют.
		:param subgroup: Подгруппа, в которой сообщение было отредактировано пользователем.
		:param user: Пользователь, который установил реакцию.
		"""

		raise NotImplementedError

	async def handle_telegram_message_read(self, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		"""
		Метод, вызываемый ботом, в случае прочтения сообщения в группе-диалоге (или топик-диалоге) в боте при помощи команды `/read` либо нажатия кнопки "прочитать".

		:param subgroup: Подгруппа, в которой сообщение было прочитано.
		:param user: Пользователь, который прочитал сообщение.
		"""

		raise NotImplementedError

	async def handle_telegram_callback_button(self, query: CallbackQuery, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		"""
		Метод, вызываемый ботом при нажатии на кнопку в сообщении в группе-диалоге (или топик-диалоге). Данный метод вызывается только при нажатии на кнопки, которые были скопированы с сервиса.

		:param query: Callback query из Telegram.
		:param subgroup: Подгруппа, в которой сообщение было прочитано.
		:param user: Пользователь, который прочитал сообщение.
		"""

		raise NotImplementedError

	async def get_message_by_telegram_id(self, service_owner_id: int, message_id: int) -> Optional["TelehooperMessage"]:
		"""
		Возвращает информацию о отправленном через бота сообщения по его ID в Telegram.

		:param service_owner_id: ID пользователя сервиса, который связан с этим сообщением.
		:param message_id: ID сообщения в Telegram.
		"""

		raise NotImplementedError

	async def get_message_by_service_id(self, service_owner_id: int, message_id: int) -> Optional["TelehooperMessage"]:
		"""
		Возвращает информацию о отправленном через бота сообщения по его ID в сервисе.

		:param service_owner_id: ID пользователя сервиса, который связан с этим сообщением.
		:param message_id: ID сообщения в сервисе.
		"""

		raise NotImplementedError

	@staticmethod
	async def reconnect_on_restart(user: "TelehooperUser", db_user: Document, bot: Bot) -> Optional["BaseTelehooperServiceAPI"]:
		"""
		Выполняет переподключение сервиса после перезагрузки бота. Если переподключение успешно, возвращает класс сервиса, иначе - None.

		:param user: Telegram-пользователь, которому принадлежит сервис.
		:param db_user: Документ с данными пользователя из БД.
		"""

		raise NotImplementedError

	async def update_last_activity(self) -> None:
		"""
		Сохраняет в БД время последнего взаимодействия с данным сервисом (поле `LastActivityAt`).
		"""

		raise NotImplementedError

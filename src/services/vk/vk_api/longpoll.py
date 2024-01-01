# coding: utf-8

import asyncio
from asyncio import TimeoutError
from typing import AsyncGenerator, Optional

import aiohttp
from aiohttp import ClientConnectionError
from loguru import logger

from services.vk.utils import VKLongpollMessageFlags
from services.vk.vk_api.api import VKAPI


class BaseVKLongpollEvent:
	"""
	Базовое событие Longpoll ВКонтакте.

	Неофициальная документация Longpoll: https://danyadev.github.io/longpoll-doc/
	"""

	event_type: int
	"""Тип события. Список событий: https://dev.vk.com/api/user-long-poll/getting-started#Структура событий"""
	event_data: list
	"""Информация о событии."""
	event_raw: list
	"""Неотредактированное содержимое события, которое было получено напрямую с longpoll-сервера."""

	def __init__(self, event: list) -> None:
		self.event_type = event[0]
		self.event_data = event[1:]

		self.event_raw = event

	@staticmethod
	def get_event_type(event: list, raise_error: bool = True) -> Optional["BaseVKLongpollEvent"]:
		"""
		Автоматически определяет тип события, выдавая нужный класс longpoll-события.

		:param event: Событие, полученное с longpoll-сервера.
		:param raise_error: Выбрасывать ли ошибку, если тип события неизвестен. Если False, то возвращает None.
		"""

		event_type = event[0]

		if event_type == 10004 and len(event) > 3:
			# В редких случаях, ВКонтакте возвращает событие о новом сообщении (т.е., LongpollNewMessageEvent)
			# с очень странным содержимым: в таком событии есть лишь 2 поля, предположительно:
			# - ID сообщения.
			# - Дата в UNIX.
			#
			# Всех остальных полей (по типу текста, ID отправителя и всего такого) нет.
			# Что бы избежать странных ошибок, обработка такого типа событий здесь исключается.

			return LongpollNewMessageEvent(event)
		elif event_type == 63:
			return LongpollTypingEventMultiple(event)
		elif event_type == 64:
			return LongpollVoiceMessageEvent(event)
		elif event_type == 10005:
			return LongpollMessageEditEvent(event)
		elif event_type == 10002:
			return LongpollMessageFlagsEdit(event)

		if raise_error:
			raise ValueError(f"Неизвестный тип события: {event_type}")

		return None

class LongpollNewMessageEvent(BaseVKLongpollEvent):
	"""
	Longpoll-событие, вызываемое при получении нового сообщения ВКонтакте.

	ID события: `10004`.
	"""

	conversation_message_id: int
	"""ID сообщения относительно текущей беседы."""
	flags: VKLongpollMessageFlags
	"""Флаги сообщения."""
	minor_id: int | None
	"""ID сообщения."""
	peer_id: int
	"""ID чата, в котором было отправлено сообщение. Для пользователя: id пользователя. Для групповой беседы: `2000000000 + id` беседы. Для сообщества: `-id` сообщества либо `id + 1000000000`."""
	timestamp: int
	"""UNIX-время отправки данного сообщения."""
	text: str
	"""Текст сообщения."""

	# Объект с дополнительными данными.
	_additional_: dict
	"""Дополнительные поля."""
	title: str | None
	"""Титульник сообщения."""
	emoji: bool | None
	"""Наличие эмодзи в сообщении."""
	from_id: int | None
	"""ID отправителя сообщения."""
	has_template: bool | None
	"""Наличие шаблона."""
	marked_users: list | None
	"""Упомянутые пользователи в сообщении."""
	keyboard: object | None
	"""Объект клавиатуры от ботом."""
	expire_ttl: int | None
	"""Количество секунд до исчезновения сообщения."""
	ttl: int | None
	"""Количество секунд до исчезновения сообщения в фантомном чате."""
	is_expired: bool | None
	"""Указывает, что сообщение исчезло."""
	payload: str | None
	"""Полезная нагрузка сообщения."""
	source_act: str | None
	"""Действие, которое было совершено с сообщением. Например, `chat_kick_user`."""
	source_text: str | None
	"""Текст, который связан с `source_act`."""
	source_old_text: str | None
	"""Старый текст, который связан с `source_act`."""
	source_message_id: int | None
	"""ID пользователя, с которым связано `source_act`."""
	source_chat_local_id: int | None
	"""ID сообщения, с которым связано `source_act`."""

	attachments: dict
	"""Вложения сообщения."""

	random_id: int
	"""Случайный ID, передаваемый при отправке сообщения."""
	message_id: int
	"""ID сообщения."""
	update_timestamp: int | None
	"""UNIX-время редактирования сообщения, если оно было хоть раз отредактировано."""

	def __init__(self, event: list) -> None:
		super().__init__(event)

		self.conversation_message_id = self.event_data[0]
		self.flags = VKLongpollMessageFlags(self.event_data[1])
		self.minor_id = self.event_data[2]
		self.peer_id = self.event_data[3]
		self.timestamp = self.event_data[4]
		self.text =  self.event_data[5]

		self._additional_ = self.event_data[6]
		self.title = self._additional_.get("title", None)
		self.emoji = self._additional_.get("emoji", None) == "1"
		self.from_id = self._additional_.get("from", None)
		if self.from_id:
			self.from_id = int(self.from_id)
		self.has_template = self._additional_.get("has_template", None) == "1"
		self.marked_users = self._additional_.get("marked_users", None)
		self.keyboard = self._additional_.get("keyboard", None)
		self.expire_ttl = self._additional_.get("expire_ttl", None)
		if self.expire_ttl:
			self.expire_ttl = int(self.expire_ttl)
		self.ttl = self._additional_.get("ttl", None)
		self.is_expired = self._additional_.get("is_expired", None) == "1"
		self.payload = self._additional_.get("payload", None)
		self.source_act = self._additional_.get("source_act")
		self.source_message_id = self._additional_.get("source_mid")
		if self.source_message_id:
			self.source_message_id = int(self.source_message_id)
		self.source_chat_local_id = self._additional_.get("source_chat_local_id")
		if self.source_chat_local_id:
			self.source_chat_local_id = int(self.source_chat_local_id)
		self.source_text = self._additional_.get("source_text")
		self.source_old_text = self._additional_.get("source_old_text")

		self.attachments = self.event_data[7]

		self.random_id = self.event_data[8]
		self.message_id = self.event_data[9]
		self.update_timestamp = self.event_data[10] or None

class LongpollTypingEventMultiple(BaseVKLongpollEvent):
	"""
	Longpoll-событие, вызываемое когда в беседе начинает печатать сразу несколько пользователей.

	ID события: `63`.
	"""

	peer_id: int
	"""Чат, в котором начали печатать сообщение."""
	user_ids: list[int]
	"""ID пользователей, которые печатают сообщение. Максимальное количество в данном объекте - 5 пользователей."""
	total_count: int
	"""Количество пользователей, которые печатают сообщение."""
	timestamp: int
	"""Время создания данного события."""

	def __init__(self, event: list) -> None:
		super().__init__(event)

		self.peer_id = self.event_data[0]
		self.user_ids = self.event_data[1]
		self.total_count = self.event_data[2]
		self.timestamp = self.event_data[3]

class LongpollVoiceMessageEvent(BaseVKLongpollEvent):
	"""
	Longpoll-событие, вызываемое когда какой-то из пользователей ВКонтакте записывает голосовое сообщение. Вызывается каждые 5~ секунд.

	ID события: `64`.
	"""

	user_ids: int
	"""ID пользователей, которые записывают голосовое сообщение. Может быть несколько, если данное событие произошло в беседе, где записывают голосовые сообщения сразу несколько людей."""
	peer_id: int
	"""Чат, в котором пользователи записывают голосовое сообщение."""

	def __init__(self, event: list) -> None:
		super().__init__(event)

		self.peer_id = self.event_data[0]
		self.user_ids = self.event_data[1]

class LongpollMessageEditEvent(BaseVKLongpollEvent):
	"""
	Longpoll-событие, вызываемое при редактировании сообщения.

	ID события: `10005`.
	"""

	flags: VKLongpollMessageFlags
	"""Флаги сообщения."""
	minor_id: int | None
	"""ID сообщения."""
	peer_id: int
	"""ID чата, в котором было отправлено сообщение. Для пользователя: id пользователя. Для групповой беседы: `2000000000 + id` беседы. Для сообщества: `-id` сообщества либо `id + 1000000000`."""
	timestamp: int
	"""UNIX-время отправки данного сообщения."""
	text: str
	"""Текст сообщения."""

	# Объект с дополнительными данными.
	_additional_: dict
	"""Дополнительные поля."""
	title: str | None
	"""Титульник сообщения."""
	emoji: bool | None
	"""Наличие эмодзи в сообщении."""
	from_id: int | None
	"""ID отправителя сообщения."""
	has_template: bool | None
	"""Наличие шаблона."""
	marked_users: list | None
	"""Упомянутые пользователи в сообщении."""
	keyboard: object | None
	"""Объект клавиатуры от ботом."""
	expire_ttl: int | None
	"""Количество секунд до исчезновения сообщения."""
	ttl: int | None
	"""Количество секунд до исчезновения сообщения в фантомном чате."""
	is_expired: bool | None
	"""Указывает, что сообщение исчезло."""
	payload: str | None
	"""Полезная нагрузка сообщения."""
	source_act: str | None
	"""Действие, которое было совершено с сообщением. Например, `chat_kick_user`."""
	source_text: str | None
	"""Текст, который связан с `source_act`."""
	source_old_text: str | None
	"""Старый текст, который связан с `source_act`."""
	source_message_id: int | None
	"""ID пользователя, с которым связано `source_act`."""
	source_chat_local_id: int | None
	"""ID сообщения, с которым связано `source_act`."""

	attachments: dict
	"""Вложения сообщения."""

	random_id: int
	"""Случайный ID, передаваемый при отправке сообщения."""
	message_id: int
	"""ID сообщения."""
	update_timestamp: int | None
	"""UNIX-время редактирования сообщения, если оно было хоть раз отредактировано."""

	def __init__(self, event: list) -> None:
		super().__init__(event)

		self.flags = VKLongpollMessageFlags(self.event_data[0])
		self.minor_id = self.event_data[1]
		self.peer_id = self.event_data[2]
		self.timestamp = self.event_data[3]
		self.text =  self.event_data[4]

		self._additional_ = self.event_data[5]
		self.title = self._additional_.get("title", None)
		self.emoji = self._additional_.get("emoji", None) == "1"
		self.from_id = self._additional_.get("from", None)
		if self.from_id:
			self.from_id = int(self.from_id)
		self.has_template = self._additional_.get("has_template", None) == "1"
		self.marked_users = self._additional_.get("marked_users", None)
		self.keyboard = self._additional_.get("keyboard", None)
		self.expire_ttl = self._additional_.get("expire_ttl", None)
		if self.expire_ttl:
			self.expire_ttl = int(self.expire_ttl)
		self.ttl = self._additional_.get("ttl", None)
		self.is_expired = self._additional_.get("is_expired", None) == "1"
		self.payload = self._additional_.get("payload", None)
		self.source_act = self._additional_.get("source_act")
		self.source_message_id = self._additional_.get("source_mid")
		if self.source_message_id:
			self.source_message_id = int(self.source_message_id)
		self.source_chat_local_id = self._additional_.get("source_chat_local_id")
		if self.source_chat_local_id:
			self.source_chat_local_id = int(self.source_chat_local_id)
		self.source_text = self._additional_.get("source_text")
		self.source_old_text = self._additional_.get("source_old_text")

		self.attachments = self.event_data[6]

		self.random_id = self.event_data[7]
		self.message_id = self.event_data[8]
		self.update_timestamp = self.event_data[9] or None

class LongpollMessageFlagsEdit(BaseVKLongpollEvent):
	"""
	Longpoll-событие, вызываемое при редактировании флагов сообщения.

	ID события: `10002`.
	"""

	conversation_message_id: int
	"""ID сообщения в беседе."""
	new_flags: VKLongpollMessageFlags
	"""Новые флаги сообщения."""
	peer_id: int
	"""Чат, в котором было изменены флаги сообщения."""

	def __init__(self, event: list) -> None:
		super().__init__(event)

		self.conversation_message_id = self.event_data[0]
		self.new_flags = VKLongpollMessageFlags(self.event_data[1])
		self.peer_id = self.event_data[2]

class VKAPILongpoll:
	"""
	Longpoll для ВКонтакте.

	Код был взят с vkbottle: https://github.com/vkbottle/vkbottle/blob/master/vkbottle/polling/user_polling.py
	"""

	wait: int
	"""Время ожидания между запросами к longpoll-серверу. ВКонтакте автоматически 'завершает' свой ответ после данного значения."""
	mode: int
	"""Режим работы longpoll-сервера."""
	is_stopped: bool = False
	"""Остановлен ли longpoll. Если данное значение установить на True, то longpoll будет остановлен."""
	version: int
	"""Версия Longpoll."""

	def __init__(self, api: VKAPI, wait: int = 50, mode: int = 1706, version: int = 19):
		self.api = api

		self.wait = wait
		self.mode = mode
		self.version = version

	def stop(self) -> None:
		"""
		Останавливает текущий Longpoll, если он запущен.
		"""

		if not self.is_stopped:
			self.is_stopped = True

	async def get_longpoll_event(self, server: dict) -> dict:
		"""
		Получает событие с longpoll-сервера.

		Предупреждение: Ввиду того, как работает longpoll, данный метод выполяется очень долго, если нету никаких событий со стороны ВКонтакте.
		"""

		async with aiohttp.ClientSession() as session:
			async with session.post(f"https://{server['server']}?act=a_check&key={server['key']}&ts={server['ts']}&wait={self.wait}&mode={self.mode}&version={self.version}") as response:
				return await response.json()

	async def get_longpoll_server(self) -> dict:
		"""
		Возвращает информацию о longpoll-сервере. API: `messages.getLongPollServer`.
		"""

		return await self.api.messages_getLongPollServer()

	async def listen_for_raw_updates(self) -> AsyncGenerator[dict, None]:
		"""
		Генератор для прослушки raw-событий с longpoll-сервера.
		Вместо этого метода рекомендуется использовать метод `listen_for_updates`.

		Пример использования:
		```python
		async for event in longpoll.listen_for_updates():
		    print(event)
		```
		"""

		retries = 0
		server: dict | None = None

		while not self.is_stopped:
			try:
				if not server:
					server = await self.get_longpoll_server()

				longpoll_event = await self.get_longpoll_event(server)

				if "ts" not in longpoll_event:
					server = None

					continue

				server["ts"] = longpoll_event["ts"]
				retries = 0

				yield longpoll_event
			except (TimeoutError, ClientConnectionError):
				retries += 1
				server = None

				await asyncio.sleep(0.25 * retries)

	async def listen_for_updates(self) -> AsyncGenerator[BaseVKLongpollEvent, None]:
		"""
		Генератор для прослушки событий с longpoll-сервера.

		Пример использования:
		```python
		async for event in longpoll.listen_for_updates():
		    print(event)
		```
		"""

		while not self.is_stopped:
			async for event in self.listen_for_raw_updates():
				# Если нет никаких обновлений, то просто скипаем.
				if event.get("updates") is None:
					continue

				for update in event["updates"]:
					event = BaseVKLongpollEvent.get_event_type(update, raise_error=False)

					if not event:
						logger.debug(f"[VK] Неизвестный тип события: {update[0]}: {update[1:]}")

						continue

					yield event

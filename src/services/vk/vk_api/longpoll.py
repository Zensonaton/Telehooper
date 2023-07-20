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

		if event_type == 4:
			return LongpollNewMessageEvent(event)

		if raise_error:
			raise ValueError(f"Неизвестный тип события: {event_type}")

		return None

class LongpollNewMessageEvent(BaseVKLongpollEvent):
	"""
	Longpoll-событие, вызываемое при получении нового сообщения ВКонтакте.

	ID события: `4`.
	"""

	message_id: int
	"""ID сообщения."""
	date: int
	"""UNIX-время отправки сообщения."""
	peer_id: int
	"""ID отправителя сообщения."""
	text: str
	"""Текст сообщения."""
	flags: VKLongpollMessageFlags
	"""Флаги сообщения."""
	attachments: dict
	"""Вложения сообщения."""

	def __init__(self, event: list) -> None:
		super().__init__(event)

		self.message_id = self.event_data[0]
		self.flags = VKLongpollMessageFlags(self.event_data[1])
		self.peer_id = self.event_data[2]
		self.date = self.event_data[3]
		self.text = self.event_data[5]
		self.attachments = self.event_data[6]

class VKAPILongpoll:
	"""
	Longpoll для ВКонтакте.

	Код был взят с vkbottle: https://github.com/vkbottle/vkbottle/blob/master/vkbottle/polling/user_polling.py
	"""

	wait: int
	"""Время ожидания между запросами к longpoll-серверу. ВКонтакте автоматически 'завершает' свой ответ после данного значения."""
	mode: int
	"""Режим работы longpoll-сервера."""
	user_id: int | None
	"""ID пользователя, для которого будет работать longpoll. Если не указано, то будет использован ID текущего пользователя."""
	is_stopped: bool = False
	"""Остановлен ли longpoll. Если данное значение установить на True, то longpoll будет остановлен."""

	def __init__(self, api: VKAPI, wait: int = 50, mode: int = 682, user_id: int | None = None):
		self.api = api

		self.wait = wait
		self.mode = mode
		self.user_id = user_id

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
			async with session.post(f"https://{server['server']}?act=a_check&key={server['key']}&ts={server['ts']}&wait={self.wait}&mode={self.mode}") as response:
				return await response.json()

	async def get_longpoll_server(self) -> dict:
		"""
		Возвращает информацию о longpoll-сервере. API: `messages.getLongPollServer`.
		"""

		if self.user_id is None:
			self.user_id = (await self.api.account_getProfileInfo())["id"]

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
				if not event["updates"]:
					continue

				for update in event["updates"]:
					event = BaseVKLongpollEvent.get_event_type(update, raise_error=False)

					if not event:
						continue

					yield event

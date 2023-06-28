# coding: utf-8

import asyncio
from asyncio import TimeoutError
from typing import AsyncGenerator

import aiohttp
from aiohttp import ClientConnectionError
from loguru import logger

from services.vk.vk_api.api import VKAPI


class BaseVKLongpollEvent:
	"""
	Базовое событие Longpoll ВКонтакте.
	"""

	event_type: int
	event_data: list
	event_raw: list

	def __init__(self, event: list) -> None:
		self.event_type = event[0]
		self.event_data = event[1:]

		self.event_raw = event

	@staticmethod
	def get_event_type(event: list, raise_error: bool = True):
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

	pass

class VKAPILongpoll:
	"""
	Longpoll для ВКонтакте.

	Код был взят с vkbottle: https://github.com/vkbottle/vkbottle/blob/master/vkbottle/polling/user_polling.py
	"""

	wait: int
	mode: int
	rps_delay: int = 0
	user_id: int | None
	is_stopped: bool = False

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
			async with session.post(f"https://{server['server']}?act=a_check&key={server['key']}&ts={server['ts']}&wait={self.wait}&mode={self.mode}&rps_delay={self.rps_delay}") as response:
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

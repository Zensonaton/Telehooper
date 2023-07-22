# coding: utf-8

import asyncio
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import (Audio, Document, Message, PhotoSize, TelegramObject,
                           Video)


_cache: dict[str, list] = {}

class AlbumMiddleware(BaseMiddleware):
	"""
	Middleware, собирающий медиагруппы в один объект, передавая handler'ам поле `album` с фото/видео/аудио/документами из медиагруппы. В данный момент не используется.
	"""

	latency: float
	"""Задержка в секундах, которая будет использоваться для сбора медиагруппы."""

	def __init__(self, latency: float = 0.5) -> None:
		"""
		Инициализирует middleware.

		:param latency: Задержка в секундах, которая будет использоваться для сбора медиагруппы.
		"""

		self.latency = latency

	@staticmethod
	def get_content(message: Message) -> PhotoSize | Video | Audio | Document | None:
		"""
		Извлекает медиа-контент из сообщения.

		:param message: Сообщение, из которого нужно извлечь медиа-контент.
		"""

		if message.photo:
			return message.photo[-1]

		if message.video:
			return message.video

		if message.audio:
			return message.audio

		if message.document:
			return message.document

		return None

	async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
		"""
		Метод, вызываемый при каждом вызове Handler'ов aiogram.
		"""

		if isinstance(event, Message):
			if event.media_group_id is not None:
				key = event.media_group_id

				# Если уже существует медиагруппа с таким ключом, то просто добавляем сообщение в кэш медиагруппы.
				if key in _cache:
					_cache[key].append(event)

					return None

				# Если медиагруппы с таким ключом нет, то создаём её.
				_cache[key] = [event]


				async def _smth() -> None:
					# Спим некоторое время что бы получить все сообщения из медиагруппы,
					# и потом добавляем медиагруппу в data, что бы обработчик мог её получить.
					await asyncio.sleep(self.latency)
					data["album"] = [self.get_content(message) for message in _cache[key].copy()]

					del _cache[key]

					await handler(event, data)

				asyncio.create_task(_smth())
				return

			# Если мы можем извлечь хотя бы один объект из сообщения, то добавляем его в data.
			content = self.get_content(event)

			if content:
				data["album"] = [content]

		return await handler(event, data)

# coding: utf-8

import asyncio

from aiogram.types import User
from loguru import logger
from pydantic import SecretStr

from services.service_api_base import BaseTelehooperServiceAPI
from services.vk.vk_api.api import VKAPI
from services.vk.vk_api.longpoll import VKAPILongpoll


class VKServiceAPI(BaseTelehooperServiceAPI):
	"""
	Service-API для ВКонтакте.
	"""

	token: SecretStr
	user: User

	def __init__(self, token: SecretStr, user: User) -> None:
		self.token = token
		self.user = user

	async def start_listening(self) -> asyncio.Task:
		async def _handle_updates() -> None:
			longpoll = VKAPILongpoll(
				VKAPI(self.token)
			)

			async for event in longpoll.listen_for_updates():
				logger.debug(f"Got event with type {event.__class__.__name__} and data {event.event_data}")

		return asyncio.create_task(_handle_updates())

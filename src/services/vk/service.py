# coding: utf-8

import asyncio

from aiogram.types import User
from loguru import logger
from pydantic import SecretStr

from services.service_api_base import BaseTelehooperServiceAPI
from services.vk.vk_api.api import VKAPI, VKAPILongpoll


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
			api = VKAPI(self.token)
			longpoll = VKAPILongpoll(api)

			async for event in longpoll.listen_for_raw_updates():
				logger.debug(f"Got event from longpoll: {event}")

		return asyncio.create_task(_handle_updates())

# coding: utf-8

import asyncio
from typing import cast

import aiohttp
from pydantic import SecretStr

from service_api_base import BaseTelehooperServiceAPI
from services.vk.utils import random_id


INVISIBLE_CHARACTER = "&#12288;"

class VKAPI:
	"""
	API для использования методов ВКонтакте.

	Данный класс предоставляет низкоуровневый доступ к определённым API-запросам ВКонтакте.
	"""

	token: SecretStr
	version: str

	def __init__(self, token: SecretStr, api_version: str = "5.131") -> None:
		"""
		Инициализация API.

		:param token: Токен для доступа к API ВКонтакте.
		"""

		self.token = token
		self.version = api_version

	async def _get_(self, method: str, params: dict[str, str | int | bool] | None = None) -> dict:
		"""
		Выполняет GET-запрос к API ВКонтакте.

		:param method: Метод API.
		:param params: Параметры запроса.
		"""

		if params is None:
			params = {}

		params["access_token"] = self.token.get_secret_value()
		params["v"] = self.version

		async with aiohttp.ClientSession() as session:
			async with session.get(f"https://api.vk.com/method/{method}", params=params) as response:
				response_json = await response.json()

				if response_json.get("error"):
					raise Exception(response_json["error"]["error_msg"])

				return response_json["response"]

	async def _post_(self, method: str, params: dict[str, str | int | bool] | None = None) -> dict:
		"""
		Выполняет POST-запрос к API ВКонтакте.

		:param method: Метод API.
		:param params: Параметры запроса.
		"""

		if params is None:
			params = {}

		params["access_token"] = self.token.get_secret_value()
		params["v"] = self.version

		async with aiohttp.ClientSession() as session:
			async with session.post(f"https://api.vk.com/method/{method}", params=params) as response:
				response_json = await response.json()

				if response_json.get("error"):
					raise Exception(response_json["error"]["error_msg"])

				return response_json["response"]

	async def account_getProfileInfo(self) -> dict:
		"""
		Получает информацию об аккаунте. API: `account.getProfileInfo`.
		"""

		return await self._get_("account.getProfileInfo")

	async def users_get(self, user_ids: list[int]) -> dict:
		"""
		Получает информацию о пользователях. API: `users.get`.

		:param user_ids: Список ID пользователей.
		"""

		return await self._get_("users.get", {
			"user_ids": ",".join(map(str, user_ids)),
			"fields": "photo_100" # TODO: Дать возможность выбора полей.
		})

	async def get_self_info(self, user_id: int | None = None) -> dict:
		"""
		Получает информацию о данном аккаунте ВКонтаке (с которым ассоциирован данный токен), вызывая поочерёдно API-методы `account.getProfileInfo` (если `user_id` не дан) и `users.get` для получения подробной информации.

		:param user_id: ID пользователя, информацию о котором необходимо получить. Если не указано, то будет использован ID текущего пользователя.
		"""

		if user_id is None:
			account_info = await self.account_getProfileInfo()

			user_id = cast(int, account_info["id"])

		user_info = await self.users_get([user_id])

		return user_info[0]

	async def messages_send(self, peer_id: int, message: str) -> dict:
		"""
		Отправляет сообщение пользователю. API: `messages.send`.

		:param peer_id: ID пользователя/группы/беседы, в которую будет отправлено сообщение.
		:param message: Текст сообщения.
		"""

		return await self._post_("messages.send", {
			"peer_id": peer_id,
			"message": message,
			"random_id": random_id()
		})

class VKServiceAPI(BaseTelehooperServiceAPI):
	"""
	Service-API для ВКонтакте.
	"""

	...

# coding: utf-8

import asyncio
from typing import cast

import aiohttp
from pydantic import SecretStr

from service_api_base import BaseTelehooperServiceAPI
from services.vk.exceptions import AccountDeactivatedException, BaseVKAPIException
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

	def _parse_response(self, response: dict) -> dict:
		"""
		Парсит ответ от ВКонтакте.
		"""

		if response.get("error"):
			code = response["error"]["error_code"]
			message = response["error"]

			if code in [3610, 17]:
				raise AccountDeactivatedException(message=message)
			else:
				raise BaseVKAPIException(
					error_code=code,
					message=message
				)

		return response["response"]

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
				return self._parse_response(await response.json())

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
				return self._parse_response(await response.json())

	async def account_getProfileInfo(self) -> dict:
		"""
		Получает информацию об аккаунте. API: `account.getProfileInfo`.
		"""

		return await self._get_("account.getProfileInfo")

	async def users_get(self, user_ids: list[int]) -> dict:
		"""
		Получает информацию о пользователях. API: `users.get`.
		В данном методе извлекается вся доступная информация о пользователе (все возможные значения для `fields`).

		:param user_ids: Список ID пользователей.
		"""

		fields = "activities, about, blacklisted, blacklisted_by_me, books, bdate, can_be_invited_group, can_post, can_see_all_posts, can_see_audio, can_send_friend_request, can_write_private_message, career, common_count, connections, contacts, city, country, crop_photo, domain, education, exports, followers_count, friend_status, has_photo, has_mobile, home_town, photo_100, photo_200, photo_200_orig, photo_400_orig, photo_50, sex, site, schools, screen_name, status, verified, games, interests, is_favorite, is_friend, is_hidden_from_feed, last_seen, maiden_name, military, movies, music, nickname, occupation, online, personal, photo_id, photo_max, photo_max_orig, quotes, relation, relatives, timezone, tv, universities"

		return await self._get_("users.get", {
			"user_ids": ",".join(map(str, user_ids)),
			"fields": fields
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

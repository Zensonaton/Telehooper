# coding: utf-8

from typing import Any

import aiohttp
from loguru import logger
from pydantic import SecretStr

from services.vk.exceptions import (AccountDeactivatedException,
                                    BaseVKAPIException)
from services.vk.utils import random_id


ALL_USER_FIELDS = "activities, about, blacklisted, blacklisted_by_me, books, bdate, can_be_invited_group, can_post, can_see_all_posts, can_see_audio, can_send_friend_request, can_write_private_message, career, common_count, connections, contacts, city, country, crop_photo, domain, education, exports, followers_count, friend_status, has_photo, has_mobile, home_town, photo_100, photo_200, photo_200_orig, photo_400_orig, photo_50, sex, site, schools, screen_name, status, verified, games, interests, is_favorite, is_friend, is_hidden_from_feed, last_seen, maiden_name, military, movies, music, nickname, occupation, online, personal, photo_id, photo_max, photo_max_orig, quotes, relation, relatives, timezone, tv, universities"

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

		logger.debug(f"VK API response: {response}")

		if response.get("error"):
			code = response["error"]["error_code"]
			message = response["error"]

			if code in [3610, 17, 18]:
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

	async def users_get(self, user_ids: list[int] | None = None) -> dict:
		"""
		Получает информацию о пользователях. API: `users.get`.
		В данном методе извлекается вся доступная информация о пользователе (все возможные значения для `fields`).

		:param user_ids: Список ID пользователей. Если не указано, то будет использован ID текущего пользователя.
		"""

		data: dict[str, Any] = {"fields": ALL_USER_FIELDS}
		if user_ids:
			data["user_ids"] = ",".join(map(str, user_ids))

		return await self._get_("users.get", data)

	async def get_self_info(self, user_id: int | None = None) -> dict:
		"""
		Получает информацию о данном аккаунте ВКонтаке (с которым ассоциирован данный токен). API: `users.get`.

		:param user_id: ID пользователя, информацию о котором необходимо получить. Если не указано, то будет использован ID текущего пользователя.
		"""

		return (await self.users_get([user_id] if user_id else []))[0]

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

	async def messages_getLongPollServer(self) -> dict:
		"""
		Выдаёт информацию о longpoll-сервере. API: `messages.getLongPollServer`.
		"""

		return await self._post_("messages.getLongPollServer")

	async def messages_getConversations(self, offset: int = 0, count: int = 200, extended: bool = True) -> dict:
		"""
		Выдаёт список из бесед пользователя. API: `messages.getConversations`.
		"""

		return await self._get_("messages.getConversations", {
			"offset": offset,
			"count": count,
			"extended": 1 if extended else 0,
			"fields": ALL_USER_FIELDS
		})

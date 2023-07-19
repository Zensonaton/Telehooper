# coding: utf-8

import asyncio
from typing import TYPE_CHECKING, Optional, cast

from aiogram.types import Chat, Message
from loguru import logger
from pydantic import SecretStr

import utils
from config import config
from DB import get_user
from services.service_api_base import (BaseTelehooperServiceAPI,
                                       ServiceDialogue,
                                       ServiceDisconnectReason,
                                       TelehooperServiceUserInfo)
from services.vk.vk_api.api import VKAPI
from services.vk.vk_api.longpoll import (BaseVKLongpollEvent,
                                         LongpollNewMessageEvent,
                                         VKAPILongpoll)

if TYPE_CHECKING:
	from api import TelehooperMessage, TelehooperSubGroup, TelehooperUser


class VKServiceAPI(BaseTelehooperServiceAPI):
	"""
	Service-API для ВКонтакте.
	"""

	token: SecretStr
	"""Токен для доступа к API ВКонтакте."""
	vkAPI: VKAPI
	"""Объект для доступа к API ВКонтакте."""

	_cachedDialogues = []
	"""Кэшированный список диалогов."""
	_longPollTask: asyncio.Task | None = None
	"""Задача, выполняющая longpoll."""

	def __init__(self, token: SecretStr, vk_user_id: int, user: "TelehooperUser") -> None:
		super().__init__("VK", vk_user_id, user)

		self.token = token
		self.user = user

		self.vkAPI = VKAPI(self.token)

	async def start_listening(self) -> asyncio.Task:
		# TODO: Обработка ошибок этой функции. (asyncio.Task)

		async def _handle_updates() -> None:
			longpoll = VKAPILongpoll(self.vkAPI)

			async for event in longpoll.listen_for_updates():
				await self.handle_update(event)

		self._longPollTask = asyncio.create_task(_handle_updates())
		return self._longPollTask

	async def handle_update(self, event: BaseVKLongpollEvent) -> None:
		"""
		Метод, обрабатывающий события VK Longpoll.

		:param event: Событие, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		logger.debug(f"[VK] Новое событие {event.__class__.__name__}: {event.event_data}")

		if type(event) is LongpollNewMessageEvent:
			subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(
				self.user,
				ServiceDialogue(
					service_name=self.service_name,
					id=event.from_id
				)
			)

			if not subgroup:
				return

			logger.debug(f"[VK] Новое сообщение с текстом \"{event.text}\", для подгруппы \"{subgroup.service_dialogue_name}\"")

			sent_by_account_owner = event.from_id == self.service_user_id
			ignore_self_debug = config.debug and await self.user.get_setting("Debug.SentViaBotInform")

			# Проверяем, стоит ли боту обрабатывать исходящие сообщения.
			if sent_by_account_owner and not (await self.user.get_setting("Services.ViaServiceMessages") or ignore_self_debug):
				return

			# Проверяем, не было ли отправлено сообщение самим ботом.
			msg_saved = await subgroup.service.get_message_by_service_id(event.message_id)

			if msg_saved and msg_saved.sent_via_bot and not ignore_self_debug:
				return

			try:
				new_message_text = ""

				if sent_by_account_owner:
					new_message_text = f"[<b>Вы</b>{' <i>debug-пересылка</i>' if ignore_self_debug else ''}]: "

				new_message_text += event.text

				telegram_message_id = await subgroup.send_message_in(new_message_text, silent=sent_by_account_owner)

				await TelehooperAPI.save_message("VK", telegram_message_id, event.message_id, False)
			except Exception as e:
				# TODO: Отправлять сообщение об ошибке пользователю, делая при этом логирование самого текста ошибки.

				logger.error(f"Ошибка отправки сообщения Telegram-пользователю {utils.get_telegram_logging_info(self.user.telegramUser)}: {e}")

	async def get_list_of_dialogues(self, force_update: bool = False, max_amount: int = 800, skip_ids: list[int] = []) -> list[ServiceDialogue]:
		if not force_update and self._cachedDialogues:
			return self._cachedDialogues

		extendedInfo = {}
		retrieved_dialogues = 0
		total_dialogues = 0
		result = []

		while True:
			response = await self.vkAPI.messages_getConversations(offset=retrieved_dialogues)
			if not total_dialogues:
				total_dialogues = response["count"]

			# ВК очень странно возвращает информацию о списке диалогов,
			# вместо
			#   {информации о диалоге, имя юзера и всё такое}
			# ВК возвращает
			#   {{информация о диалоге}, [{id: имя юзера и всё такое}, ...]}
			#
			# Данный кусок кода немного упрощает это, создавая словарь с информацией.
			for group in response.get("groups", []):
				extendedInfo.update({
					-group["id"]: group
				})

			for user in response.get("profiles", []):
				extendedInfo.update({
					user["id"]: user
				})

			for dialogue in response["items"]:
				convo = dialogue["conversation"]

				conversation_id = convo["peer"]["id"]
				conversation_type = convo["peer"]["type"]
				convo_extended = extendedInfo.get(conversation_id)

				# Про тип "email" можно почитать здесь:
				# https://dev.vk.com/reference/objects/message
				#
				# К сожалению, данный тип бесед имеет отличия от обычных диалогов.
				# Смысла добавлять поддержку такого типа нету, поскольку
				# такие беседы создавать уже не является возможным во ВКонтакте.
				if conversation_type == "email":
					total_dialogues -= 1

					continue

				if conversation_id in skip_ids:
					total_dialogues -= 1

					continue

				full_name = ""
				image_url = "https://vk.com/images/camera_200.png"

				if not convo_extended and conversation_type != "chat":
					raise Exception(f"Не удалось найти расширенную информацию о диалоге {conversation_id}, хотя она обязана быть.")

				if conversation_type == "chat":
					full_name = convo["chat_settings"]["title"]

					if "photo" in convo["chat_settings"]:
						image_url = convo["chat_settings"]["photo"]["photo_200"]
				elif conversation_type == "user":
					convo_extended = cast(dict, convo_extended)

					full_name = f"{convo_extended['first_name']} {convo_extended['last_name']}"
					image_url = convo_extended.get("photo_max")
				elif conversation_type == "group":
					convo_extended = cast(dict, convo_extended)

					full_name = convo_extended["name"]
					image_url = convo_extended.get("photo_max")
				else:
					raise Exception(f"Неизвестный тип диалога {conversation_type}.")

				result.append(
					ServiceDialogue(
						service_name=self.service_name,
						id=conversation_id,
						name=full_name,
						profile_url=image_url,
						is_multiuser=conversation_type == "chat",
						is_pinned=convo["sort_id"]["major_id"] > 0,
						is_muted="push_settings" in convo and convo["push_settings"]["disabled_forever"]
					)
				)

				retrieved_dialogues += 1

			if retrieved_dialogues >= total_dialogues or retrieved_dialogues >= max_amount:
				break

		self._cachedDialogues = result
		return result

	def has_cached_list_of_dialogues(self) -> bool:
		return bool(self._cachedDialogues)

	async def disconnect_service(self, reason: ServiceDisconnectReason = ServiceDisconnectReason.INITIATED_BY_USER) -> None:
		db_user = await get_user(self.user.telegramUser)

		assert "VK" in db_user["Connections"]

		try:
			if reason not in [ServiceDisconnectReason.INITIATED_BY_USER, ServiceDisconnectReason.ISSUED_BY_ADMIN]:
				raise Exception

			await self.vkAPI.messages_send(
				peer_id=db_user["Connections"]["VK"]["ID"],
				message="ℹ️ Telegram-бот «Telehooper» был отключён от Вашей страницы ВКонтакте."
			)
		except:
			pass

		# Удаляем из БД.
		del db_user["Connections"]["VK"]

		await db_user.save()

		# Удаляем VKServiceAPI из памяти.
		self.user.remove_vk_connection()

		# Отключаем longpoll.
		if self._longPollTask:
			logger.debug("Cancelling longpoll task...")

			self._longPollTask.cancel()

		# Удаляем из памяти.
		del self.token
		del self.vkAPI
		del self._cachedDialogues
		del self._longPollTask

	async def current_user_info(self) -> TelehooperServiceUserInfo:
		self_info = await self.vkAPI.get_self_info()

		return TelehooperServiceUserInfo(
			service_name=self.service_name,
			id=self_info["id"],
			name=f"{self_info['first_name']} {self_info['last_name']}",
			profile_url=self_info.get("photo_max_orig"),
		)

	async def get_dialogue(self, chat_id: int, force_update: bool = False) -> ServiceDialogue:
		dialogues = await self.get_list_of_dialogues(force_update=force_update)

		for dialogue in dialogues:
			if dialogue.id == chat_id:
				return dialogue

		raise TypeError(f"Диалог с ID {chat_id} не найден")

	async def send_message(self, chat_id: int, text: str) -> int:
		return await self.vkAPI.messages_send(peer_id=chat_id, message=text)

	async def handle_inner_message(self, msg: Message, subgroup: "TelehooperSubGroup") -> None:
		from api import TelehooperAPI


		logger.debug(f"[TG] Обработка сообщения в Telegram: \"{msg.text}\" в \"{subgroup}\"")

		service_message_id = await self.send_message(
			chat_id=self.service_user_id,
			text=msg.text or "[пустой текст сообщения]"
		)
		await TelehooperAPI.save_message("VK", msg.message_id, service_message_id, True)

	async def get_message_by_telegram_id(self, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		from api import TelehooperAPI

		return await TelehooperAPI.get_message_by_telegram_id("VK", message_id, bypass_cache=bypass_cache)

	async def get_message_by_service_id(self, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		from api import TelehooperAPI

		return await TelehooperAPI.get_message_by_service_id("VK", message_id, bypass_cache=bypass_cache)

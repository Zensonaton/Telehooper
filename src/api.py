# coding: utf-8

import asyncio
import base64
import random
from typing import Any, Literal, Sequence, cast

import aiohttp
import cachetools
from aiocouch import Document, NotFoundError
from aiogram import Bot
from aiogram.exceptions import (TelegramAPIError, TelegramBadRequest,
                                TelegramForbiddenError)
from aiogram.filters import Command
from aiogram.filters.command import CommandPatternType
from aiogram.types import Audio, BufferedInputFile, CallbackQuery, Chat
from aiogram.types import Document as TelegramDocument
from aiogram.types import (ForceReply, InlineKeyboardMarkup, InputFile,
                           InputMediaAudio, InputMediaDocument,
                           InputMediaPhoto, InputMediaVideo, Message,
                           PhotoSize, ReplyKeyboardMarkup, ReplyKeyboardRemove,
                           Sticker, User, Video, VideoNote, Voice)
from loguru import logger
from magic_filter import MagicFilter
from pyrate_limiter import BucketFullException, Limiter, RequestRate

import utils
from config import config
from DB import get_db, get_default_subgroup, get_group
from DB import get_user as db_get_user
from exceptions import DisallowedInDebugException
from services.service_api_base import BaseTelehooperServiceAPI, ServiceDialogue
from services.vk.service import VKServiceAPI
from settings import SETTINGS_TREE, SettingsHandler


# Да, я знаю что это плохой способ. Знаю. Ни к чему другому, адекватному я не пришёл.
_saved_connections = {}
_service_dialogues: list["TelehooperSubGroup"] = []
_cached_message_ids: dict[int, list["TelehooperMessage"]] = {}
_cached_attachments: list["TelehooperCachedAttachment"] = []
_media_group_messages: dict[str, list] = {}

settings = SettingsHandler(SETTINGS_TREE)

class TelehooperUser:
	"""
	Пользователь бота Telehooper.
	"""

	creation_date: int
	"""UNIX-Время первого сообщения пользователя боту."""
	botBanned: bool
	"""Заблокировал ли пользователь бота?"""
	settingsOverriden: dict
	"""Словарь из настроек, которые были переопределены пользователем."""
	knownLanguage: str | None
	"""Язык, который известен боту."""
	roles: list[str]
	"""Роли пользователя."""
	connections: dict
	"""Список подключённых сервисов."""
	document: Document
	"""Документ пользователя в БД."""
	telegramUser: User
	"""Объект пользователя в Telegram."""

	def __init__(self, document: Document, user: User) -> None:
		"""
		Инициализирует объект пользователя.

		:param document: Документ пользователя в БД.
		:param user: Объект пользователя в Telegram.
		"""

		self.document = document
		self.telegramUser = user
		self._parse_document(document)

	def _parse_document(self, user: Document) -> None:
		"""
		Парсит значение документа пользователя в объект пользователя.

		:param user: Документ пользователя в БД.
		"""

		self.creation_date = user["CreationDate"]
		self.botBanned = user["BotBanned"]
		self.settingsOverriden = user["SettingsOverriden"]
		self.knownLanguage = user["KnownLanguage"]
		self.roles = user["Roles"]
		self.connections = user["Connections"]

	async def refresh_document(self) -> Document:
		"""
		Изменяет значения переменных данного класа, что бы соответствовать документу в БД.
		"""

		self.document = await db_get_user(self.telegramUser)
		self._parse_document(self.document)

		return self.document

	def _get_service_store_name(self, name: str) -> str:
		"""
		Возвращает название ключа в словаре `connections` для сохранения API сервиса.

		:param name: Название сервиса.
		"""

		return f"{self.telegramUser.id}-{name}"

	def save_connection(self, service_api: BaseTelehooperServiceAPI) -> None:
		"""
		Сохраняет ServiceAPI в объект пользователя. После сохранения в память, извлечь API можно через методы по типу `get_vk_connection`.

		:param service_api: ServiceAPI, который нужно сохранить.
		"""

		_saved_connections[self._get_service_store_name(service_api.service_name)] = service_api

	def _get_connection(self, name: str) -> BaseTelehooperServiceAPI | None:
		"""
		Возвращает ServiceAPI из объекта пользователя. Если API не был сохранён, возвращается None. Рекомендуется вместо этого использовать методы по типу `get_vk_connection`.

		:param name: Название сервиса.
		"""

		return _saved_connections.get(self._get_service_store_name(name))

	def _remove_connection(self, name: str) -> None:
		"""
		Удаляет ServiceAPI из объекта пользователя.

		:param name: Название сервиса.
		"""

		_saved_connections.pop(self._get_service_store_name(name), None)

	def get_vk_connection(self) -> VKServiceAPI | None:
		"""
		Возвращает ServiceAPI для ВКонтакте из объекта пользователя.

		Если API не был сохранён, возвращается None.
		"""

		return cast(VKServiceAPI, self._get_connection("VK"))

	def remove_vk_connection(self) -> None:
		"""
		Удаляет ServiceAPI для ВКонтакте из объекта пользователя.
		"""

		self._remove_connection("VK")

	def has_role(self, role: str, allow_any: bool = True) -> bool:
		"""
		Проверяет, есть ли у пользователя роль `role`.

		:param role: Роль, которую нужно проверить.
		:param allow_any: Если `True`, то при наличии роли `*` у пользователя возвращается `True`.
		"""

		if allow_any and "*" in self.roles:
			return True

		return role.lower() in [i.lower() for i in self.roles]

	async def restrict_in_debug(self) -> None:
		"""
		Вызывает Exception, если включён debug-режим у бота, а пользователь не имеет роли "tester".
		"""

		await TelehooperAPI.restrict_in_debug(self)

	async def get_setting(self, path: str, force_refresh: bool = False) -> Any:
		"""
		Возвращает значение настройки по пути `path`. Вызывает исключение, если настройка не найдена.

		:param path: Путь к настройке.
		:param force_refresh: Обновить ли документ пользователя в БД перед получением настройки.
		"""

		if force_refresh:
			await self.refresh_document()

		return self.settingsOverriden.get(path, settings.get_default_setting_value(path))

	async def save_setting(self, path: str, new_value: Any) -> None:
		"""
		Сохраняет настройку по пути `path` в БД. Если новое значение настройки не отличается от значения по-умолчанию, то бот не сохранит данную запись. Вызовет исключение, если настройка не существует.

		:param path: Путь к настройке.
		:param new_value: Новое значение настройки.
		"""

		is_default = settings.get_default_setting_value(path) == new_value

		if is_default:
			self.document["SettingsOverriden"].pop(path, None)
			self.settingsOverriden = self.document["SettingsOverriden"]

			await self.document.save()

			return

		self.document["SettingsOverriden"].update({path: new_value})
		self.settingsOverriden = self.document["SettingsOverriden"]
		await self.document.save()

	async def get_connected_groups(self, bot: Bot | None = None) -> list["TelehooperGroup"]:
		"""
		Возвращает список из всех подключённых TelehooperGroup, с которым связан данный пользователь.

		Если, по какой-то причине, запись в БД у пользователя ссылается на несуществующую группу, то запись о таковой группе будет удалена.

		:param bot: Объект бота. Если не передан, будет попытка извлечь его самостоятельно.
		"""

		db = await get_db()

		if not bot:
			bot = Bot.get_current()
			assert bot

		groups = []

		for index, group in enumerate([await get_group(i) for i in self.document["Groups"]]):
			if not group:
				# Если нам не удалось получить информацию о группе, то мы получим "пустой" документ.
				# В таком случае, нужно просто удалить группу из списка групп пользователя.
				group_id = self.document["Groups"][index]

				logger.warning(f"У пользователя {utils.get_telegram_logging_info(self.telegramUser)} была обнаружена ссылка на несуществующую Telegram-группу с ID {group_id}, она будет удалена.")

				self.document["Groups"].remove(group_id)
				await self.document.save()

				continue

			# Создаём объект данной группы.
			group_id = group["ID"]

			try:
				telegram_group = await bot.get_chat(group_id)
				groups.append(TelehooperGroup(self, group, telegram_group, bot))
			except (TelegramForbiddenError, TelegramBadRequest):
				logger.debug(f"Удаляю Telegram-группу {group_id} для пользователя {utils.get_telegram_logging_info(self.telegramUser)}, поскольку бот не смог получить о ней информацию.")

				await TelehooperAPI.delete_group_data(group_id, fully_delete=True, bot=bot)

		return groups

class TelehooperGroup:
	"""
	Класс с информацией о группе, которая связана с каким-либо сервисом.
	"""

	id: int
	"""ID данной группы в Telegram."""
	creatorID: int
	"""ID пользователя Telegram, который является создателем (администратором) данной группы."""
	createdAt: int
	"""UNIX-Время создания группы."""
	lastActivityAt: int
	"""UNIX-Время последней активности в группе."""
	userJoinedWarning: bool
	"""Указывает, отправлял ли бот предупреждение о том, что сторонний пользователь вступил в группу."""
	statusMessageID: int
	"""ID статусного сообщения, которое было закреплено в группе."""
	adminRights: bool
	"""Имеет ли бот права администратора в группе."""
	minibots: list[str]
	"""@username добавленных миниботов данной группы."""
	associatedMinibots: dict[str, str]
	"""Словарь, состоящий из связи ID пользователей сервиса и @username минибота в Telegram."""
	chats: dict
	"""Список диалогов в группе."""
	services: dict
	"""Информация, настройки сервисов в данной группе."""

	creator: TelehooperUser
	"""Создатель группы."""
	document: Document
	"""Документ группы в БД."""
	chat: Chat
	"""Объект группы в Telegram."""
	bot: Bot
	"""Объект "главного" бота Telehooper в Telegram."""

	limiter: Limiter
	"""Лимитер для этой группы."""

	def __init__(self, creator: TelehooperUser, document: Document, chat: Chat, bot: Bot) -> None:
		"""
		Инициализирует объект группы.

		:param creator: Создатель группы.
		:param document: Документ группы в БД.
		:param chat: Объект группы в Telegram.
		:param bot: Объект бота в Telegram.
		"""

		self.document = document
		self.creator = creator
		self.chat = chat
		self.bot = bot

		self._parse_document(document)

		# 1 сообщение в секунду,
		# 20 сообщений в минуту.
		self.limiter = Limiter(RequestRate(1, 1), RequestRate(20, 60))

	def _parse_document(self, group: Document) -> None:
		"""
		Парсит значение документа группы в объект группы.

		:param group: Документ группы в БД.
		"""

		self.id = group["ID"]
		self.creatorID = group["Creator"]
		self.createdAt = group["CreatedAt"]
		self.lastActivityAt = group["LastActivityAt"]
		self.userJoinedWarning = group["UserJoinedWarning"]
		self.statusMessageID = group["StatusMessageID"]
		self.adminRights = group["AdminRights"]
		self.minibots = group["Minibots"]
		self.associatedMinibots = group["AssociatedMinibots"]
		self.chats = group["Chats"]
		self.services = group["Services"]

	async def refresh_document(self) -> Document:
		"""
		Изменяет значения переменных данного класа, что бы соответствовать документу в БД.
		"""

		group_db = await get_group(self.id)
		assert group_db, "Данные об объекте группы не были получены из БД"

		self.document = group_db
		self._parse_document(self.document)

		return self.document

	async def acquire_queue(self, key: str, max_delay: int | float | None = None) -> bool:
		"""
		Пытается получить место в очереди. Если место не было получено, то бот будет спать до тех пор, пока не получит место. Возвращает `True`, если место было получено, иначе `False`, если места вообще нет.

		:param key: Ключ, по которому нужно получить место в очереди.
		:param max_delay: Максимальное время ожидания в секундах. Если ожидание превысит это время, то метод вернёт `False`.
		"""

		while True:
			try:
				self.limiter.try_acquire(key)
			except BucketFullException as err:
				delay_time = float(err.meta_info["remaining_time"])

				exceeded_max_delay = max_delay and delay_time > max_delay
				if exceeded_max_delay:
					return False

				await asyncio.sleep(delay_time)
			else:
				return True

	def get_bucket_size(self, key: str) -> int:
		"""
		Возвращает 'заполненность' очереди по заданному имени.

		:param key: Ключ, по которому нужно получить заполненность очереди.
		"""

		try:
			return self.limiter.get_current_volume(key)
		except:
			return 0

	async def convert_to_dialogue_group(self, user: TelehooperUser, dialogue: ServiceDialogue, pinned_message: Message, serviceAPI: BaseTelehooperServiceAPI) -> None:
		"""
		Конвертирует данную Telegram-группу в группу-диалог из сервиса. Данный метод изменяет название, фотографию, а так же описание группы. Помимо этого, она сохраняет информацию о созданной группе в БД.

		:param user: Пользователь, который создал группу-диалог.
		:param dialogue: Диалог, который нужно сохранить.
		:param pinned_message: Сообщение, которое используется как статусное.
		:param serviceAPI: API сервиса, который нужно использовать для отправки сообщений.
		"""

		async def _sleep():
			await asyncio.sleep(1)

		async def _longSleep():
			await asyncio.sleep(4)

		thread_id = 0 if not pinned_message.is_topic_message else (pinned_message.message_thread_id or 0)

		allow_group_params_copy = await user.get_setting("Services.VK.SyncGroupInfo")
		allow_group_url = await user.get_setting("Security.GetChatURL")

		# Пытаемся изменить название группы.
		if allow_group_params_copy and dialogue.name:
			try:
				title = dialogue.name
				if config.debug and await user.get_setting("Debug.DebugTitleForDialogues"):
					title = f"[DEBUG] {title}"

				await self.set_title(title)
			except:
				await _longSleep()
			else:
				await _sleep()

		# Пытаемся изменить фотографию группы.
		if allow_group_params_copy and (dialogue.profile_img or dialogue.profile_url):
			picture_bytes = dialogue.profile_img
			if dialogue.profile_url:
				async with aiohttp.ClientSession() as session:
					async with session.get(dialogue.profile_url) as response:
						picture_bytes = await response.read()

			assert picture_bytes

			try:
				await self.chat.set_photo(photo=BufferedInputFile(file=picture_bytes, filename="photo.png"))
			except:
				await _longSleep()
			else:
				await _sleep()

		# Пытаемся поменять описание группы.
		if allow_group_params_copy:
			try:
				await self.chat.set_description(
					f"@{utils.get_bot_username()}: Группа для диалога «{dialogue.name}» из ВКонтакте.\n"
					"\n"
					"ℹ️ Для управления данной группой используйте команду /this."
				)
			except:
				await _longSleep()
			else:
				await _sleep()

		# Пытаемся получить ссылку на группу, если это разрешено пользователем.
		group_url = None
		if allow_group_url:
			try:
				chat_link = (await self.chat.create_invite_link("[Telehooper] Ссылка на чат", creates_join_request=True)).invite_link

				# Удаляем https://t.me/ из начала ссылки; Мы должны сохранить только часть после слеша.
				chat_link = chat_link.split("/")[-1]

				# Безопасности ради, шифруем ключём.
				group_url = utils.encrypt_with_env_key(chat_link)
			except:
				await _longSleep()
			else:
				await _sleep()

		# Сохраняем в память.
		TelehooperAPI.save_subgroup(
			TelehooperSubGroup(
				id=thread_id,
				dialogue_name=dialogue.name,
				service=serviceAPI,
				parent=self,
				service_chat_id=dialogue.id
			)
		)

		# Обновляем значения из БД.
		await user.refresh_document()

		# Делаем изменения в БД.
		# Сохраняем информацию о пользователе.
		if not self.chat.id in user.document["Groups"]:
			user.document["Groups"].append(self.chat.id)

		# Сохраняем информацию о группе.
		self.document["LastActivityAt"] = utils.get_timestamp()
		self.document["URL"] = group_url
		self.document["Chats"][str(thread_id)] = get_default_subgroup(
			topic_id=thread_id,
			service_name=dialogue.service_name,
			dialogue_id=dialogue.id,
			dialogue_name=dialogue.name or "Без названия",
			pinned_message=pinned_message.message_id,
			type="dialogue"
		)

		# Сохраняем информацию о диалоге пользователя.
		user.document["Connections"]["VK"]["OwnedGroups"][str(dialogue.id)] = {
			"ID": dialogue.id,
			"Name": dialogue.name,
			"IsMultiuser": dialogue.is_multiuser,
			"GroupID": self.chat.id,
			"TopicID": thread_id,
			"Type": "dialogue",
			"URL": group_url
		}

		await user.document.save()
		await self.document.save()

	async def get_associated_bot(self, sender_id: int | None = None) -> Bot:
		"""
		Возвращает объект Telegram-бота, ассоциированный с указанным по его ID пользователем. Используется в группах, связанных с беседами из сервисов, где добавлены миниботы. Если ассоциированный минибот не найден, то тогда будет возвращён объект "основного" бота.

		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		"""

		from telegram.bot import get_minibots


		# Если нам не передан ID отправителя, то просто возвращаем "главного" бота.
		if not sender_id:
			return self.bot

		sender_id_str = str(sender_id)

		# Получаем словарь тех миниботов, которые есть в этой группе.
		await self.refresh_document()

		available_minibots = {username: bot for username, bot in get_minibots().items() if username in self.minibots}
		free_minibots = {username: bot for username, bot in available_minibots.items() if username not in self.associatedMinibots.values()}

		# Если нет ни одного минибота, то просто возвращаем "главного" бота.
		if not available_minibots:
			return self.bot

		# Если такого пользователя нет в списке ассоциированных, то присваиваем случайного.
		if not sender_id_str in self.associatedMinibots:
			# Получаем рандомного бота.
			# Если возможно, рандомно выбираем того, который ещё не использовался.
			# В ином случае, берём из общего пула.
			random_minibot_username = random.choice(list((free_minibots or available_minibots).keys()))

			self.document["AssociatedMinibots"][sender_id_str] = random_minibot_username
			await self.document.save()

		# Извлекаем объект минибота по его @username.
		minibot = available_minibots.get(self.associatedMinibots[sender_id_str])

		return minibot or self.bot

	async def send_sticker(self, sticker: BufferedInputFile | InputFile | str, reply_to: int | None = None, topic: int = 0, silent: bool = False, sender_id: int | None = None, bypass_queue: bool = False) -> list[Message] | None:
		"""
		Отправляет стикер в Telegram-группу.

		:param sticker: Стикер.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param silent: Отправить ли сообщение без уведомления.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		bot = await self.get_associated_bot(sender_id)

		if not bypass_queue and not await self.acquire_queue(f"message-{bot.id}"):
			return None

		return [await bot.send_sticker(
			chat_id=self.chat.id,
			sticker=sticker,
			message_thread_id=topic,
			reply_to_message_id=reply_to,
			disable_notification=silent,
			allow_sending_without_reply=True
		)]

	async def send_geo(self, latitude: float, longitude: float, reply_to: int | None = None, topic: int = 0, silent: bool = False, sender_id: int | None = None, bypass_queue: bool = False) -> list[Message] | None:
		"""
		Отправляет геолокацию в Telegram-группу.

		:param latitude: Широта.
		:param longitude: Долгота.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param silent: Отправить ли сообщение без уведомления.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		bot = await self.get_associated_bot(sender_id)

		if not bypass_queue and not await self.acquire_queue(f"message-{bot.id}"):
			return None

		return [await bot.send_location(
			chat_id=self.chat.id,
			latitude=latitude,
			longitude=longitude,
			message_thread_id=topic,
			reply_to_message_id=reply_to,
			disable_notification=silent,
			allow_sending_without_reply=True
		)]

	async def send_video_note(self, video_note: BufferedInputFile | InputFile | str, reply_to: int | None = None, topic: int = 0, silent: bool = False, sender_id: int | None = None, bypass_queue: bool = False) -> list[Message] | None:
		"""
		Отправляет видео-сообщение (кружочек) в Telegram-группу.

		:param video_note: Видео-сообщение.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param silent: Отправить ли сообщение без уведомления.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		bot = await self.get_associated_bot(sender_id)

		if not bypass_queue and not await self.acquire_queue(f"message-{bot.id}"):
			return None

		return [await bot.send_video_note(
			chat_id=self.chat.id,
			video_note=video_note,
			message_thread_id=topic,
			reply_to_message_id=reply_to,
			disable_notification=silent,
			allow_sending_without_reply=True
		)]

	async def send_message(self, text: str, attachments: list[InputMediaAudio | InputMediaDocument | InputMediaPhoto | InputMediaVideo] | None = None, reply_to: int | None = None, topic: int = 0, silent: bool = False, keyboard: InlineKeyboardMarkup | None = None, disable_web_preview: bool = False, sender_id: int | None = None, bypass_queue: bool = False) -> list[int] | None:
		"""
		Отправляет сообщение в группу. Возвращает ID отправленного(-ых) сообщений.

		:param text: Текст сообщения.
		:param attachments: Telegram-вложения.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param silent: Отправить ли сообщение без уведомления.
		:param keyboard: Клавиатура, которую нужно прикрепить к сообщению.
		:param disable_web_preview: Отключить ли превью ссылок в сообщении.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли сообщение без учёта очереди.
		"""

		bot = await self.get_associated_bot(sender_id)

		if not bypass_queue and not await self.acquire_queue(f"message-{bot.id}"):
			return None

		if not attachments:
			attachments = []

		# В Telegram, при отправке медиа-группы, поле "caption" выступает как текст сообщения, отображаемое сверху сообщения.
		# По этой причине, тут мы меняем текст вложения на текст сообщения, которое мы пытаемся отправить.
		if attachments:
			attachments[0].caption = text

		# У нас есть хотя бы одно вложение, отправляем как медиа-группу.
		if attachments:
			return [i.message_id for i in await bot.send_media_group(
				chat_id=self.chat.id,
				media=attachments,
				message_thread_id=topic,
				reply_to_message_id=reply_to,
				disable_notification=silent,
				allow_sending_without_reply=True
			)]

		# Вложений нету, отправляем как сообщение без вложений.
		return [(await bot.send_message(
			chat_id=self.chat.id,
			message_thread_id=topic,
			reply_to_message_id=reply_to,
			text=text,
			disable_notification=silent,
			allow_sending_without_reply=True,
			reply_markup=keyboard,
			disable_web_page_preview=disable_web_preview
		)).message_id]

	async def start_activity(self, type: Literal["typing", "upload_photo", "record_video", "upload_video", "record_audio", "upload_audio", "upload_document", "find_location", "record_video_note", "upload_video_note"] = "typing", topic: int = 0, sender_id: int | None = None, bypass_queue: bool = False) -> None:
		"""
		Начинает событие в Telegram-группе по типу печати, записи голосового сообщения и подобных.

		:param type: Тип события.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли событие печати, минуя очередь.
		"""

		bot = await self.get_associated_bot(sender_id)

		if not bypass_queue and not await self.acquire_queue(f"message-{bot.id}"):
			return None

		await bot.send_chat_action(
			chat_id=self.chat.id,
			action=type,
			message_thread_id=topic
		)

	async def edit_message(self, new_text: str, id: int, sender_id: int | None = None, bypass_queue: bool = False) -> None:
		"""
		Редактирует сообщение в Telegram-группе.

		:param new_text: Новый текст сообщения.
		:param id: ID сообщения, которое нужно отредактировать.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отредактировать ли сообщение, минуя очередь.
		"""

		bot = await self.get_associated_bot(sender_id)

		if not bypass_queue and not await self.acquire_queue(f"message-{bot.id}"):
			return None

		try:
			await bot.edit_message_text(
				text=new_text,
				chat_id=self.chat.id,
				message_id=id
			)
		except TelegramBadRequest:
			# Если мы пытаемся отредачить сообщение с медиа (к примеру, фото), то нужно использовать метод `edit_message_caption`.

			await bot.edit_message_caption(
				caption=new_text,
				chat_id=self.chat.id,
				message_id=id
			)

	async def delete_message(self, id: list[int] | int, sender_id: int | None = None, bypass_queue: bool = False) -> None:
		"""
		Удаляет одно или несколько сообщений в Telegram-группе.

		:param id: ID сообщения(-ий), которое нужно удалить.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Удалить ли указанное сообщение, минуя очередь.
		"""

		bot = await self.get_associated_bot(sender_id)

		if not bypass_queue and not await self.acquire_queue(f"message-{bot.id}"):
			return None

		if isinstance(id, int):
			id = [id]

		for message_id in id:
			await bot.delete_message(
				self.chat.id,
				message_id=message_id
			)

	async def set_title(self, title: str) -> None:
		"""
		Устанавливает название группы в Telegram.

		:param title: Новое название группы.
		"""

		await self.bot.set_chat_title(self.chat.id, title)

	async def set_description(self, description: str) -> None:
		"""
		Устанавливает описание группы в Telegram.

		:param description: Новое описание группы.
		"""

		await self.bot.set_chat_description(self.chat.id, description)

	async def set_photo(self, photo: BufferedInputFile | InputFile) -> None:
		"""
		Устанавливает фотографию группы в Telegram.

		:param photo: Новая фотография группы.
		"""

		await self.bot.set_chat_photo(self.chat.id, photo=photo)

	async def remove_photo(self) -> None:
		"""
		Удаляет фотографию группы в Telegram.
		"""

		await self.bot.delete_chat_photo(self.chat.id)

	async def pin_message(self, message_id: int, disable_notification: bool = False) -> None:
		"""
		Закрепляет сообщение в Telegram-группе.

		:param message_id: ID сообщения, которое нужно закрепить.
		:param disable_notification: Отправить ли сообщение без уведомления.
		"""

		await self.bot.pin_chat_message(self.chat.id, message_id=message_id, disable_notification=disable_notification)

	async def unpin_message(self, message_id: int | None = None) -> None:
		"""
		Открепляет сообщение в Telegram-группе.
		"""

		await self.bot.unpin_chat_message(self.chat.id, message_id)

	async def unpin_all_messages(self) -> None:
		"""
		Открепляет все сообщения в Telegram-группе.
		"""

		await self.bot.unpin_all_chat_messages(self.chat.id)

	def get_subgroups(self) -> list["TelehooperSubGroup"]:
		"""
		Возвращает список сервис-диалогов, связанных с данной группой.
		"""

		return [i for i in TelehooperAPI.get_all_subgroups() if i.parent.chat.id == self.chat.id]

class TelehooperMessage:
	"""
	Класс, описывающий сообщение отправленного через Telehooper. Данный класс предоставляет доступ к ID сообщения в сервисе и в Telegram, а так же прочую информацию.
	"""

	service: str
	"""Название сервиса, через который было отправлено сообщение."""
	telegram_message_ids: list[int]
	"""Список ID сообщений в Telegram. Может быть несколько, если сообщение является альбомом."""
	service_message_ids: list[int]
	"""Список ID сообщений в сервисе. Может быть несколько, если сообщение является альбомом."""
	service_conversation_message_ids: list[int] | None
	"""Список ID сообщений в сервисе относительно беседы, а не текущего пользователя. Может быть несколько, если сообщение является альбомом."""
	sent_via_bot: bool
	"""Отправлено ли сообщение через бота."""

	def __init__(self, service: str, telegram_mids: int | list[int], service_mids: int | list[int], service_conv_mids: int | list[int] | None = None, sent_via_bot: bool = False) -> None:
		"""
		Инициализирует объект сообщения.

		:param service: Название сервиса, через который было отправлено сообщение.
		:param telegram_mids: ID сообщения(-ий) в Telegram.
		:param service_mids: ID сообщения(-ий) в сервисе.
		:param service_conv_mids: ID сообщения(-ий) в сервисе относительно беседы.
		:param sent_via_bot: Отправлено ли сообщение через бота.
		"""

		self.service = service
		self.telegram_message_ids = [telegram_mids] if isinstance(telegram_mids, int) else telegram_mids
		self.service_message_ids = [service_mids] if isinstance(service_mids, int) else service_mids
		self.service_conversation_message_ids = [service_conv_mids] if isinstance(service_conv_mids, int) else service_conv_mids
		self.sent_via_bot = sent_via_bot

class TelehooperCachedAttachment:
	"""
	Класс, описывающий вложение, которое было сохранено в Telegram. Данный класс предоставляет доступ к ID вложения в Telegram и в сервисе, а так же прочую информацию.
	"""

	service_name: str
	"""Имя сервиса, с которым ассоциировано вложение."""
	key: str
	"""Ключ вложения в БД. Захеширован при помощи SHA-256."""
	value: str
	"""Значение вложения в БД. Зашифровано при помощи Fernet, ключ - `key` (до хэширования)."""

	def __init__(self, service_name: str, key: str, value: str) -> None:
		"""
		Инициализирует объект вложения.

		:param service_name: Имя сервиса, с которым ассоциировано вложение.
		:param key: Ключ вложения в БД. Захеширован при помощи SHA-256.
		:param value: Значение вложения в БД. Зашифровано при помощи Fernet, ключ - `key` (до хэширования).
		"""

		self.service_name = service_name
		self.key = key
		self.value = value

class TelehooperSubGroup:
	"""
	Класс для под-группы в группе-диалоге. Используется для всех диалогов внутри группы Telegram. Класс существует поскольку группы могут быть топиками с множеством диалогов.
	"""

	id: int
	"""ID топика Telegram. Может быть значением `0`, если это главная группа, которая не имеет топиков."""
	service_dialogue_name: str | None
	"""Название диалога в сервисе. В некоторых случаях может отсутствовать."""
	parent: TelehooperGroup
	"""Группа, являющаяся родителем данной суб-группы."""
	service: BaseTelehooperServiceAPI
	"""API сервиса."""
	service_chat_id: int
	"""ID диалога в сервисе."""
	pre_message_cache: cachetools.TTLCache[str, int | None] # 150 элементов, 60 секунд жизни.
	"""Кэш сообщений и их ID, который создаётся перед отправкой сообщения в сервис. Используется в случае, если отправитель сообщения не является владельцем группы."""
	callback_buttons_info: cachetools.TTLCache[str, str] # 150 элементов, 20 минут жизни.
	"""Информация о Callback-кнопках бота."""

	def __init__(self, id: int, dialogue_name: str | None, service: BaseTelehooperServiceAPI, parent: TelehooperGroup, service_chat_id: int) -> None:
		"""
		Инициализирует объект суб-группы.

		:param id: ID топика Telegram. Может быть значением `0`, если это главная группа, которая не имеет топиков.
		:param dialogue_name: Название диалога в сервисе. В некоторых случаях может отсутствовать.
		:param service: API сервиса.
		:param parent: Группа, являющаяся родителем данной суб-группы.
		:param service_chat_id: ID диалога в сервисе.
		"""

		self.id = id
		self.service_dialogue_name = dialogue_name
		self.service = service
		self.parent = parent
		self.service_chat_id = service_chat_id
		self.pre_message_cache = cachetools.TTLCache(150, 60)
		self.callback_buttons_info = cachetools.TTLCache(150, 20 * 60)

	async def send_sticker(self, sticker: BufferedInputFile | InputFile | str, reply_to: int | None = None, silent: bool = False, sender_id: int | None = None, bypass_queue: bool = False) -> list[Message] | None:
		"""
		Отправляет стикер в Telegram-группу.

		:param sticker: Стикер.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param silent: Отправить ли сообщение без уведомления.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		return await self.parent.send_sticker(
			sticker,
			reply_to=reply_to,
			topic=self.id,
			silent=silent,
			sender_id=sender_id,
			bypass_queue=bypass_queue
		)

	async def send_geo(self, latitude: float, longitude: float, reply_to: int | None = None, silent: bool = False, sender_id: int | None = None, bypass_queue: bool = False) -> list[Message] | None:
		"""
		Отправляет геолокацию в Telegram-группу.

		:param latitude: Широта.
		:param longitude: Долгота.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param silent: Отправить ли сообщение без уведомления.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		return await self.parent.send_geo(
			latitude,
			longitude,
			reply_to=reply_to,
			topic=self.id,
			silent=silent,
			sender_id=sender_id,
			bypass_queue=bypass_queue
		)

	async def send_video_note(self, input: BufferedInputFile | InputFile | str, reply_to: int | None = None, silent: bool = False, sender_id: int | None = None, bypass_queue: bool = False) -> list[Message] | None:
		"""
		Отправляет видео-сообщение (кружочек) в Telegram-группу.

		:param video_note: Видео-сообщение.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param silent: Отправить ли сообщение без уведомления.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		return await self.parent.send_video_note(
			input,
			reply_to=reply_to,
			topic=self.id,
			silent=silent,
			sender_id=sender_id,
			bypass_queue=bypass_queue
		)

	async def send_message_in(self, text: str, attachments: list[InputMediaAudio | InputMediaDocument | InputMediaPhoto | InputMediaVideo] | None = None, reply_to: int | None = None, silent: bool = False, keyboard: InlineKeyboardMarkup | None = None, disable_web_preview: bool = False, sender_id: int | None = None, bypass_queue: bool = False) -> list[int] | None:
		"""
		Отправляет сообщение в Telegram-группу.

		:param text: Текст сообщения.
		:param attachments: URL-адреса вложений.
		:param reply_to: ID сообщения, на которое нужно ответить.
		:param silent: Отправить ли сообщение без уведомления.
		:param keyboard: Клавиатура, которую нужно прикрепить к сообщению.
		:param disable_web_preview: Отключить ли превью ссылок.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли сообщение без учёта лимитов.
		"""

		return await self.parent.send_message(
			text,
			attachments=attachments,
			topic=self.id,
			silent=silent,
			reply_to=reply_to,
			keyboard=keyboard,
			disable_web_preview=disable_web_preview,
			sender_id=sender_id,
			bypass_queue=bypass_queue
		)

	async def start_activity(self, type: Literal["typing", "upload_photo", "record_video", "upload_video", "record_audio", "upload_audio", "upload_document", "find_location", "record_video_note", "upload_video_note"] = "typing", sender_id: int | None = None, bypass_queue: bool = False) -> None:
		"""
		Начинает событие в Telegram-группе по типу печати, записи голосового сообщения и подобных.

		:param type: Тип события.
		:param topic: ID диалога в сервисе, в который нужно отправить сообщение. Если не указано, то сообщение будет отправлено в главный диалог группы.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли событие печати без учёта лимитов.
		"""

		return await self.parent.start_activity(
			type,
			topic=self.id,
			sender_id=sender_id,
			bypass_queue=bypass_queue
		)

	async def edit_message(self, new_text: str, id: int, sender_id: int | None = None, bypass_queue: bool = False) -> None:
		"""
		Редактирует сообщение в Telegram-группе.

		:param new_text: Новый текст сообщения.
		:param id: ID сообщения, которое нужно отредактировать.
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		:param bypass_queue: Отправить ли событие печати без учёта лимитов.
		"""

		return await self.parent.edit_message(
			new_text,
			id=id,
			sender_id=sender_id,
			bypass_queue=bypass_queue
		)

	async def delete_message(self, id: list[int] | int, sender_id: int | None = None) -> None:
		"""
		Удаляет одно или несколько сообщений Telegram.

		:param id: ID сообщения(-ий).
		:param sender_id: ID пользователя, с которым должен быть найден ассоциированный минибот.
		"""

		await self.parent.delete_message(
			id,
			sender_id=sender_id
		)

	async def send_message_out(self, text: str) -> None:
		"""
		Отправляет сообщение в сервис.

		:param text: Текст сообщения.
		"""

		await self.service.send_message(
			chat_id=self.parent.chat.id,
			text=text
		)

	async def get_service_by_sender(self, sender: TelehooperUser) -> BaseTelehooperServiceAPI | None:
		"""
		Возвращает ассоциированный с данным пользователем ServiceAPI. Вывод зависит от настройки `OtherUsrMsgFwd` сервиса.

		:param sender: Пользователь, для которого нужно получить ServiceAPI.
		"""

		# Обновляем объект пользователя, что бы получить актуальную информацию о настройках.
		await self.parent.creator.refresh_document()

		# Тот, кто отправил сообщение - создатель группы.
		if sender.telegramUser.id == self.parent.creator.telegramUser.id:
			return self.service

		setting_value = cast(Literal["ignore", "as-owner", "as-self"], await self.parent.creator.get_setting(f"Services.{self.service.service_name}.OtherUsrMsgFwd"))

		if setting_value == "ignore":
			return None
		elif setting_value == "as-owner":
			return self.service
		else:
			return sender._get_connection(self.service.service_name)

	async def handle_telegram_message(self, msg: Message, user: TelehooperUser, attachments: list[PhotoSize | Video | Audio | TelegramDocument | VideoNote]) -> None:
		"""
		Метод, вызываемый ботом, в случае получения нового сообщения в группе-диалоге (или топик-диалоге). Этот метод обрабатывает события, передавая их текст в сервис.

		:param msg: Сообщение из Telegram. Если бот получил сразу кучу сообщений за раз (т.е., медиагруппу), то данная переменная будет равна первому сообщения из медиагруппы.
		:param user: Пользователь, который отправил сообщение.
		:param attachments: Вложения к сообщению.
		"""

		serviceAPI = await self.get_service_by_sender(user)
		if not serviceAPI:
			return

		await serviceAPI.handle_telegram_message(msg, self, user, attachments)

	async def handle_telegram_message_delete(self, msg: Message, user: TelehooperUser) -> None:
		"""
		Метод, вызываемый ботом, в случае попытки удаления сообщения в группе-диалоге (или топик-диалоге) в боте при помощи команды `/delete`.

		:param msg: Сообщение из Telegram, которое должно быть удалено. Должно являться ответом (reply) на сообщение вместо сообщения с командой.
		:param user: Пользователь, который пытается удалить сообщение.
		"""

		serviceAPI = await self.get_service_by_sender(user)
		if not serviceAPI:
			return

		await serviceAPI.handle_telegram_message_delete(msg, self, user)

	async def handle_telegram_message_edit(self, msg: Message, user: TelehooperUser) -> None:
		"""
		Метод, вызываемый ботом, в случае попытки редактирования сообщения в группе-диалоге (или топик-диалоге).

		:param msg: Новое сообщение из Telegram.
		:param user: Пользователь, который пытается отредактировать сообщение.
		"""

		serviceAPI = await self.get_service_by_sender(user)
		if not serviceAPI:
			return

		await serviceAPI.handle_telegram_message_edit(msg, self, user)

	async def handle_telegram_message_read(self, user: TelehooperUser) -> None:
		"""
		Метод, вызываемый ботом, в случае прочтения сообщения в группе-диалоге (или топик-диалоге) в боте при помощи команды `/read` либо нажатия кнопки "прочитать".

		:param user: Пользователь, который прочитал сообщение.
		"""

		serviceAPI = await self.get_service_by_sender(user)
		if not serviceAPI:
			return

		await serviceAPI.handle_telegram_message_read(self, user)

	async def handle_telegram_callback_button(self, query: CallbackQuery, user: TelehooperUser) -> None:
		"""
		Метод, вызываемый ботом при нажатии на кнопку в сообщении в группе-диалоге (или топик-диалоге). Данный метод вызывается только при нажатии на кнопки, которые были скопированы с сервиса.

		:param query: Callback query из Telegram.
		:param user: Пользователь, который нажал на кнопку.
		"""

		serviceAPI = await self.get_service_by_sender(user)
		if not serviceAPI:
			return

		await serviceAPI.handle_telegram_callback_button(query, self, user)

	def create_callback_btn(self, service_callback_data: str) -> str:
		"""
		Создаёт ключ для Inline-Callback кнопки с севриса, возвращая ключ для Telegram.
		"""

		uuid = utils.get_uuid()

		self.callback_buttons_info[uuid] = service_callback_data
		return f"service-clbck:{uuid}"

	def get_callback_btn(self, callback_data: str) -> str | None:
		"""
		Возвращает ключ Inline-Callback кнопки с севриса по ключу из Telegram. Если ключ не обнаружен, возвращает None.
		"""

		callback_data = callback_data.strip("service-clbck:")

		return self.callback_buttons_info.get(callback_data)

	def __repr__(self) -> str:
		return f"<{self.service.service_name} TelehooperSubGroup for {self.service_dialogue_name}>"

class TelehooperAPI:
	"""
	Класс с различными API бота Telehooper.
	"""

	@staticmethod
	def get_settings() -> SettingsHandler:
		"""
		Возвращает объект SettingsHandler, который предоставляет доступ к настройкам бота.
		"""

		return settings

	@staticmethod
	async def get_user(user: User) -> TelehooperUser:
		"""
		Возвращает объект TelehooperUser.

		:param user: Объект пользователя в Telegram.
		"""

		return TelehooperUser(await db_get_user(user), user)

	@staticmethod
	async def get_user_by_id(user_id: int, bot: Bot | None = None) -> TelehooperUser | None:
		"""
		Возвращает объект TelehooperUser, либо None, если данного пользователя нет в БД, или же если он не писал боту.

		:param user_id: ID пользователя в Telegram.
		:param bot: Объект бота. Если не указано, то бот попытается получить его самостоятельно.
		"""

		if not bot:
			bot = Bot.get_current()

		assert bot

		try:
			user = (await (bot).get_chat_member(user_id, user_id)).user

			return TelehooperUser(await (await get_db())[f"user_{user_id}"], user)
		except:
			return None

	@staticmethod
	async def get_group(user: TelehooperUser, chat: Chat | int, db_group: Document | None = None) -> TelehooperGroup | None:
		"""
		Возвращает объект группы, либо None, если данной группы нет в БД, или же если бот не состоит в ней.

		:param user: Пользователь, который создал (владеет) группой.
		:param chat: Объект группы в Telegram.
		:param db_group: Документ группы в БД. Если не указано, бот попытается получить его самостоятельно.
		"""

		chat_id = chat if isinstance(chat, int) else chat.id

		bot = Bot.get_current()
		assert bot

		if not db_group:
			db_group = await get_group(chat_id)

		if not db_group:
			return None

		try:
			return TelehooperGroup(user, db_group, chat if isinstance(chat, Chat) else (await bot.get_chat(chat_id)), bot)
		except NotFoundError:
			return None

	@staticmethod
	async def restrict_in_debug(user: TelehooperUser | User | None) -> None:
		"""
		Вызывает Exception, если включён debug-режим у бота, а пользователь не имеет роли "tester".

		:param user: Пользователь, которого нужно проверить. Если не указано, то бот мгновенно вызовет Exception при включённом debug-режиме.
		"""

		_exc = DisallowedInDebugException("Вы не можете пользоваться данным функционалом при debug-режиме бота. Если Вы разработчик — добавьте в свою запись БД строку 'tester' внутри поля 'Roles', что бы пользоваться ботом, либо отключите debug-режим, удалив 'debug=True' в .env-файле")

		if not user:
			raise _exc

		if not config.debug:
			return

		if isinstance(user, User):
			user = await TelehooperAPI.get_user(user)


		if not user.has_role("tester"):
			raise _exc

	@staticmethod
	def save_subgroup(group: TelehooperSubGroup) -> None:
		"""
		Сохраняет TelehooperSubGroup в память бота с целью кэширования.

		Используйте следующие методы для получения TelehooperSubGroup:
		- `get_subgroup_by_chat`.
		- `get_subgroup_by_service_dialogue`.

		:param group: TelehooperSubGroup, который нужно сохранить.
		"""

		_service_dialogues.append(group)

	@staticmethod
	def delete_subgroup(group: TelehooperSubGroup) -> None:
		"""
		Удаляет TelehooperSubGroup из памяти бота.

		:param group: TelehooperSubGroup, который нужно удалить.
		"""

		_service_dialogues.remove(group)

	@staticmethod
	def get_all_subgroups() -> list[TelehooperSubGroup]:
		"""
		Возвращает все TelehooperSubGroup, которые были сохранены в памяти бота.
		"""

		return _service_dialogues

	@staticmethod
	def get_subgroup_by_service_dialogue(user: TelehooperUser, dialogue: ServiceDialogue) -> TelehooperSubGroup | None:
		"""
		Возвращает TelehooperSubGroup по диалогу из сервиса.

		Если группа не найдена, возвращается None.

		:param user: Пользователь, который создал (владеет) группой.
		:param dialogue: Диалог, который нужно найти.
		"""

		for servDialog in _service_dialogues:
			if servDialog.parent.creatorID != user.telegramUser.id:
				continue

			if servDialog.service.service_name != dialogue.service_name:
				continue

			if servDialog.service_chat_id != dialogue.id:
				continue

			return servDialog

		return None

	@staticmethod
	def get_subgroup_by_chat(group: TelehooperGroup, topic_id: int = 0) -> TelehooperSubGroup | None:
		"""
		Возвращает TelehooperSubGroup по чату Telegram.

		Если группа не найдена, возвращается None.

		:param group: Telegram-группа, в которой нужно найти диалог.
		:param topic_id: ID топика Telegram. Если не указано, то возвращается главная группа.
		"""

		for servDialog in _service_dialogues:
			if servDialog.parent.creatorID != group.creatorID:
				continue

			if servDialog.parent.chat.id != group.chat.id:
				continue

			if servDialog.id != topic_id:
				continue

			return servDialog

		return None

	@staticmethod
	async def save_message(service_name: str, service_owner_id: int, telegram_message_id: int | list[int], service_message_id: int | list[int], service_conv_mids: int | list[int] | None = None, sent_via_bot: bool = True):
		"""
		Сохраняет ID отправленного сообщения в БД.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param service_owner_id: ID пользователя сервиса, который связан с этим сообщением.
		:param telegram_message_id: ID сообщения(-ий) в Telegram.
		:param service_message_id: ID сообщения(-ий) в сервисе.
		:param service_conv_mids: ID сообщения(-ий) в сервисе относительно беседы.
		:param sent_via_bot: Отправлено ли сообщение через бота.
		"""

		_cached_message_ids.setdefault(service_owner_id, []).append(TelehooperMessage(
			service=service_name,
			telegram_mids=telegram_message_id,
			service_mids=service_message_id,
			service_conv_mids=service_conv_mids,
			sent_via_bot=sent_via_bot
		))

	@staticmethod
	async def delete_message(service_name: str, service_owner_id: int, telegram_message_id: int | list[int] | None = None, service_message_id: int | list[int] | None = None):
		"""
		Удаляет ID сообщения из БД с соответствием по ID сообщения сервиса или Telegram.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param service_owner_id: ID пользователя сервиса, который связан с этим сообщением.
		:param telegram_message_id: ID сообщения(-ий) в Telegram.
		:param service_message_id: ID сообщения(-ий) в сервисе.
		"""

		assert telegram_message_id or service_message_id, "Не указаны ID сообщений"

		if isinstance(telegram_message_id, int):
			telegram_message_id = [telegram_message_id]

		if isinstance(service_message_id, int):
			service_message_id = [service_message_id]

		telegram_message_id = cast(list[int], telegram_message_id)
		service_message_id = cast(list[int], service_message_id)

		for index, msg in enumerate(_cached_message_ids.get(service_owner_id, [])):
			if msg.service != service_name:
				continue

			for mid in telegram_message_id:
				if mid in msg.telegram_message_ids:
					continue

				del _cached_message_ids[service_owner_id][index]

				return

			for mid in service_message_id:
				if mid in msg.service_message_ids:
					continue

				del _cached_message_ids[service_owner_id][index]

				return

	@staticmethod
	async def get_message_by_telegram_id(service_name: str, message_id: int, service_owner_id: int) -> TelehooperMessage | None:
		"""
		Возвращает информацию о отправленном через бота сообщения по его ID в Telegram.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param message_id: ID сообщения в Telegram.
		:param service_owner_id: ID пользователя сервиса, который связан с этим сообщением.
		"""

		for msg in _cached_message_ids.get(service_owner_id, []):
			if msg.service != service_name:
				continue

			if message_id not in msg.telegram_message_ids:
				continue

			return msg

	@staticmethod
	async def get_message_by_service_id(service_name: str, message_id: int, service_owner_id: int) -> TelehooperMessage | None:
		"""
		Возвращает информацию о отправленном через бота сообщения по его ID в сервисе.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param message_id: ID сообщения в сервисе.
		:param service_owner_id: ID пользователя сервиса, который связан с этим сообщением.
		"""

		for msg in _cached_message_ids.get(service_owner_id, []):
			if msg.service != service_name:
				continue

			if message_id not in msg.service_message_ids:
				continue

			return msg

	@staticmethod
	async def save_attachment(service_name: str, key: str, value: str):
		"""
		Сохраняет вложение с уникальным ID в БД с целью кэширования. Применяется для стикеров и GIF-анимаций.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param key: Уникальный ключ вложения. Данный ключ не должен быть хэширован.
		:param value: Строка для получения вложения (например, поле `file_id` у Telegram-сообщения, либо attachment у ВК). Данное значение не должно быть зашифрованым.
		"""

		attachment = TelehooperCachedAttachment(
			service_name=service_name,
			key=utils.sha256_hash(key),
			value=utils.encrypt_with_key(value, key)
		)

		_cached_attachments.append(attachment)

		# TODO: Проверка на существование перед добавлением.
		# TODO: Сохранить в БД.

	@staticmethod
	async def get_attachment(service_name: str, key: str, bypass_cache: bool = False) -> str | None:
		"""
		Возвращает значение вложения по его уникальному ключу.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param key: Уникальный ключ вложения. Не должен быть хэширован.
		:param bypass_cache: Игнорировать ли кэш. Если да, то бот будет искать вложение только в БД.
		"""

		# Если нам это разрешено, возвращаем ID сообщения из кэша.
		if not bypass_cache:
			for attachment in _cached_attachments:
				if attachment.service_name != service_name:
					continue

				if attachment.key == utils.sha256_hash(key):
					return utils.decrypt_with_key(attachment.value, key)

		# TODO: Извлечь информацию о вложении из БД.

		return None

	@staticmethod
	async def delete_attachment(service_name: str, key: str) -> None:
		"""
		Удаляет вложение указанного сервиса по его уникальному ключу.

		:param service_name: Название сервиса, через который было отправлено сообщение.
		:param key: Уникальный ключ вложения. Не должен быть хэширован.
		"""

		# Проходим по вложениям, ищем наше вложение.
		for index, attachment in enumerate(_cached_attachments):
			if attachment.service_name != service_name:
				continue

			if attachment.key != utils.sha256_hash(key):
				continue

			del _cached_attachments[index]

			return

		# TODO: Удалить вложение из БД.

	@staticmethod
	async def edit_or_resend_message(text: str, chat_id: int, message_to_edit: Message | int | None, thread_id: int | None = None, reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply | None = None, disable_web_page_preview: bool = False, allow_sending_without_reply: bool = False, bot: Bot | None = None, query: CallbackQuery | None = None) -> Message | int | None:
		"""
		Пытается отредактировать либо отправить сообщение в группу. Возвращает объект сообщения.
		"""

		message_id = message_to_edit.message_id if isinstance(message_to_edit, Message) else message_to_edit

		bot = bot if bot else Bot.get_current()
		assert bot

		async def _send() -> Message:
			return await bot.send_message(
				chat_id=chat_id,
				message_thread_id=thread_id,
				text=text,
				allow_sending_without_reply=allow_sending_without_reply,
				disable_web_page_preview=disable_web_page_preview,
				reply_markup=reply_markup
			)

		# Если не задан ID сообщения, то отправляем новое.
		if not message_id:
			return await _send()

		assert message_id

		# Пытаемся отредактировать сообщение, если не удаётся - отправляем новое.
		try:
			assert not reply_markup or isinstance(reply_markup, InlineKeyboardMarkup)

			await bot.edit_message_text(
				chat_id=chat_id,
				message_id=message_id,
				text=text,
				reply_markup=reply_markup,
				disable_web_page_preview=disable_web_page_preview
			)

			return message_id
		except TelegramForbiddenError:
			if query:
				await query.answer("Вы удалили бота из группы.", show_alert=True)

			return None
		except TelegramAPIError as error:
			if not utils.is_useful_exception(error):
				return message_id

			if query:
				await query.answer(
					"Данное сообщение устарело!\n"
					"\n"
					"Проверьте на наличие новых сообщений от бота в этом же диалоге.",
					show_alert=True
				)

			return await _send()

	@staticmethod
	async def delete_group_data(chat: int | Chat, fully_delete: bool = True, bot: Bot | None = None) -> None:
		"""
		Полностью удаляет группу, её подгруппы и все связанные с ними данные из БД. Используется, если пользователь удалил бота из группы.

		Данный метод работает для группы в целом, даже если в ней есть топики.

		:param chat: Объект группы или её ID в Telegram.
		:param fully_delete: Совершить полное удаление данных группы из БД. Если False, то данные будут оставлены в БД, но информация о подключённых диалогах внутри группы будет удалена.
		:param bot: Объект бота. Если не указан, то бот не будет удаляться из группы.
		"""

		if isinstance(chat, Chat):
			chat = chat.id

		logger.debug(f"Группа с ID {chat} была отправлена на удаление.")

		db_group = await get_group(chat)
		if not db_group:
			return

		telehooper_user = None
		try:
			telehooper_user = await TelehooperAPI.get_user_by_id(db_group["Creator"], bot)
		except:
			pass

		# Отключаем все сервис-диалоги, связанные с этой группой.
		for i in [i for i in TelehooperAPI.get_all_subgroups() if i.parent.chat.id == chat]:
			TelehooperAPI.delete_subgroup(i)

		# Удаляем группу из памяти пользователя, если объект пользователя существует.
		if telehooper_user:
			telehooper_user.document["Groups"].remove(chat)

			for connection in telehooper_user.document["Connections"].values():
				for group in connection["OwnedGroups"].copy().values():
					if group["GroupID"] != chat:
						continue

					connection["OwnedGroups"].pop(str(group["ID"]), None)

			await telehooper_user.document.save()

		# Удаляем информацию из БД группы.
		if db_group:
			if fully_delete:
				await db_group.delete()
			else:
				db_group["LastActivityAt"] = utils.get_timestamp()
				db_group["Chats"] = {}

				await db_group.save()

		# Если нужно, удаляем бота.
		if bot:
			try:
				await bot.leave_chat(chat)
			except:
				pass

	@staticmethod
	def get_service_apis() -> list[BaseTelehooperServiceAPI]:
		"""
		Возвращает список всех `ServiceAPI`'s бота.
		"""

		return list(_saved_connections.values())

async def get_subgroup(msg_or_query: Message | CallbackQuery) -> dict | None:
	"""
	Фильтр для входящих сообщений в группе. Если данная группа является диалог-группой, то данный метод вернёт объект TelehooperSubGroup.

	:param msg_or_query: Объект сообщения или Callback query в Telegram.
	"""

	# Понятия не имею как, но бот получал свои же сообщения в данном хэндлере.
	if msg_or_query.from_user and msg_or_query.from_user.is_bot:
		return None

	msg = msg_or_query if isinstance(msg_or_query, Message) else msg_or_query.message
	assert msg, "Сообщение не было найдено"

	telehooper_user = await TelehooperAPI.get_user(cast(User, msg_or_query.from_user))
	telehooper_group = await TelehooperAPI.get_group(telehooper_user, msg.chat)

	if not telehooper_group:
		return None

	telehooper_group = cast(TelehooperGroup, telehooper_group)

	topic_id = msg.message_thread_id or 0

	# Telegram в msg.message_thread_id возвращает ID сообщения, на которое был ответ.
	# Это ломает всего бота, поэтому нам приходится костылить.
	if not msg.is_topic_message:
		topic_id = 0

	subgroup = TelehooperAPI.get_subgroup_by_chat(telehooper_group, topic_id)

	if not subgroup:
		return None

	return {"subgroup": subgroup, "user": telehooper_user}

async def get_mediagroup(msg: Message) -> dict | None:
	"""
	Заставляет Handler дождаться получения всех сообщений из которых состоит медиа-группа, собирая все вложения в один список.

	:param msg: Объект сообщения в Telegram.
	"""

	def get_content(msg: Message) -> PhotoSize | Video | Audio | TelegramDocument | Voice | Sticker | VideoNote | None:
		"""
		Извлекает медиа-контент из сообщения.

		:param message: Сообщение, из которого нужно извлечь медиа-контент.
		"""

		if msg.photo:
			return msg.photo[-1]

		if msg.video:
			return msg.video

		if msg.audio:
			return msg.audio

		if msg.document:
			return msg.document

		if msg.voice:
			return msg.voice

		if msg.sticker:
			return msg.sticker

		if msg.video_note:
			return msg.video_note

		return None

	if not msg.media_group_id:
		content = get_content(msg)
		if not content:
			return {"mediagroup": []}

		return {"mediagroup": [content]}

	media_id = msg.media_group_id

	# Если уже существует медиагруппа с таким ключом, то просто добавляем сообщение в кэш медиагруппы.
	if media_id in _media_group_messages:
		_media_group_messages[media_id].append(msg)

		return None

	# Если медиагруппы с таким ключом нет, то создаём её.
	_media_group_messages[media_id] = [msg]


	await asyncio.sleep(0.5)

	return {"mediagroup": [get_content(i) for i in _media_group_messages.pop(media_id)]}

class CommandWithDeepLink(Command):
	"""
	Фильтр для Handler'ов, который позволяет обрабатывать команды из deep-link'ов.
	"""

	def __init__(self, *values: CommandPatternType, commands: CommandPatternType | Sequence[CommandPatternType] | None = None, prefix: str = "/", ignore_case: bool = False, ignore_mention: bool = False, magic: MagicFilter | None = None):
		super().__init__(*values, commands=commands, prefix=prefix, ignore_case=ignore_case, ignore_mention=ignore_mention, magic=magic)

	async def __call__(self, message: Message, bot: Bot) -> dict | bool:
		"""
		Вызывается при каждом входящем сообщении.
		"""

		def deeplink_command() -> dict | bool:
			text = message.text or message.caption
			if not text:
				return False

			command = self.extract_command(text)

			if not command or command.command != "start":
				return False

			if not command.args:
				return False

			try:
				command_extracted = self.extract_command("/" + base64.b64decode(command.args).decode())
			except:
				return False

			if command_extracted.command not in self.commands:
				return False

			return {"command": command_extracted}

		return (await super().__call__(message, bot)) or deeplink_command()

# coding: utf-8

# В этом файле находится middle-псевдо-API, благодаря которому различные 'коннекторы' могут соединяться с основым Telegram ботом.


from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import TYPE_CHECKING, Any, List, Optional

import aiogram
import vkbottle
import vkbottle_types
import vkbottle_types.responses.account
import vkbottle_types.responses.users
from vkbottle.user import Message
from vkbottle_types.responses.groups import GroupsGroupFull
from vkbottle_types.responses.messages import MessagesConversationWithMessage
from vkbottle_types.responses.users import UsersUserFull

import Utils
from Consts import AccountDisconnectType
from DB import getDefaultCollection

if TYPE_CHECKING:
	from ServiceMAPIs.VK import VKAccount, VKMiddlewareAPI
	from TelegramBot import DialogueGroup, Telehooper

logger = logging.getLogger(__name__)

class TelehooperUser:
	"""
	Класс, отображающий пользователя бота Telehooper: тут будут все подключённые сервисы.
	"""

	TGUser: aiogram.types.User
	bot: Telehooper

	vkAccount: VKAccount
	vkMAPI: "VKMiddlewareAPI"
	isVKConnected: bool

	def __init__(self, bot: Telehooper, user: aiogram.types.User) -> None:
		self.TGUser = user
		self.bot = bot
		self.vkAccount = None # type: ignore
		self.vkMAPI = None # type: ignore
		self.isVKConnected = False


	async def restoreFromDB(self) -> None:
		"""
		Восстанавливает данные, а так же подключенные сервисы из ДБ.
		"""

		DB = getDefaultCollection()

		res = DB.find_one({"_id": self.TGUser.id})
		if res and res["Services"]["VK"]["Auth"]:
			# Аккаунт ВК подключён.

			# Подключаем ВК:
			await self.connectVKAccount(res["Services"]["VK"]["Token"], res["Services"]["VK"]["IsAuthViaPassword"])

	async def connectVKAccount(self, token: str, auth_via_password: bool, connect_longpoll: bool = True) -> VKAccount:
		"""
		Подключает новый аккаунт ВК.
		"""

		# Я ненавижу Python.
		from ServiceMAPIs.VK import VKAccount, VKMiddlewareAPI

		# Авторизуемся в ВК:
		self.vkAccount = VKAccount(token, self, auth_via_password)
		await self.vkAccount.initUserInfo()

		await asyncio.sleep(0) # Спим 0 секунд, что бы последующий код не запускался до завершения кода выше.

		self.vkMAPI = VKMiddlewareAPI(self, self.bot, self.vkAccount)

		self.isVKConnected = True

		if connect_longpoll:
			self.vkMAPI.runPolling()

		return self.vkAccount

	async def getDialogueGroupByTelegramGroup(self, telegram_group: aiogram.types.Chat | int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		return await self.bot.getDialogueGroupByTelegramGroup(telegram_group)

	async def getDialogueGroupByServiceDialogueID(self, service_dialogue_id: int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		return await self.bot.getDialogueGroupByServiceDialogueID(service_dialogue_id)

	def __str__(self) -> str:
		return f"<TelehooperUser id:{self.TGUser.id}>"

class MiddlewareAPI:
	"""
	Класс, являющийся объединением всех сервисов, в частности, их API, например, отправки сообщений, ...
	"""

	user: TelehooperUser
	bot: Telehooper

	def __init__(self, user: TelehooperUser, bot: Telehooper) -> None:
		self.user = user
		self.bot = bot


	async def onNewRecievedMessage(self, messageText: str) -> None:
		"""
		Событие, когда получено новое сообщение.
		"""

		pass

	async def onMessageEdit(self) -> None:
		"""
		Событие, когда сообщение редактируется.
		"""

	async def sendMessageIn(self, message: str, chat_id: int) -> None:
		"""
		Отправляет сообщение в Telegram.
		"""

		await self.user.TGUser.bot.send_message(chat_id, message)

	async def sendMessageOut(self, message: str) -> None:
		"""
		Отправляет сообщение в сервисе.
		"""

		pass

	async def sendServiceMessageIn(self, message: str) -> aiogram.types.Message:
		"""
		Отправляет сообщению пользователю в Telegram. При использовании функции, сообщение появится у пользователя в диалоге с ботом.
		"""

		return await self.user.TGUser.bot.send_message(self.user.TGUser.id, message)

	async def sendServiceMessageOut(self, message: str) -> None:
		"""
		Отправляет сообщение внутри сервиса. Это не обычная отправка сообщения конкретному пользователю, данная функция отправляет сообщение пользователю к самому себе; например, во ВКонтакте, сообщение будет отправлено в диалог "избранное".
		"""

		pass

	async def disconnectService(self, disconnect_type: int = AccountDisconnectType.INITIATED_BY_USER, send_service_messages: bool = True) -> None:
		"""
		Отключает сервис от бота.
		"""

		if disconnect_type != AccountDisconnectType.SILENT:
			# Это не было "тихое" отключение аккаунта, поэтому
			# отправляем сообщения пользователю Telegram.

			is_external = (disconnect_type == AccountDisconnectType.EXTERNAL)

			await self.user.TGUser.bot.send_message(
				self.user.TGUser.id,
				(
					# TODO: Поменять этот текст:
					"⚠️ Аккаунт <b>«ВКонтакте»</b> был принудительно отключён от бота Telehooper; это действие было совершено <b>внешне</b>, напримёр, <b>отозвав все сессии в настройках безопасности аккаунта</b>."
					if (is_external) else
					"ℹ️ Аккаунт <b>«ВКонтакте»</b> был успешно отключён от Telehooper."
				)
			)

		# Получаем ДБ:
		DB = getDefaultCollection()

		# И удаляем запись оттуда:
		DB.update_one(
			{
				"_id": self.user.TGUser.id
			},
			{"$set": {
				"Services.VK.Auth": False,
				"Services.VK.Token": None
			}},
			upsert=True
		)

	def __str__(self) -> str:
		return "<Base MiddlewareAPI class>"

# coding: utf-8

"""
Базовый объект API. Все сервисы должны импортировать значения из данного базового класса.
"""

import time
from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, cast

import aiogram
from Consts import MAPIServiceType
from DB import getDefaultCollection

if TYPE_CHECKING:
	from TelegramBot import Telehooper, TelehooperUser

class DialogueGroup:
	"""
	Класс, отображающий объект группы-диалога в Telegram.
	"""

	group: aiogram.types.Chat
	serviceType: int
	serviceDialogueID: int
	creatorUserID: int


	def __init__(self, group: aiogram.types.Chat, service_dialogue_id: int, telegram_creator_user_id: int, service_type: int = MAPIServiceType.VK) -> None:
		self.group = group
		self.serviceType = service_type
		self.serviceDialogueID = service_dialogue_id
		self.creatorUserID = telegram_creator_user_id

	def __str__(self) -> str:
		return f"<DialogueGroup serviceID:{self.serviceType} ID:{self.serviceDialogueID}>"

class MappedMessage:
	"""
	Класс, показывающий ID сообщений сервиса и его ID в Telegram.
	"""

	sentViaTelegram: bool
	sentViaService: bool

	telegramMID: int
	serviceMID: int
	telegramDialogueID: int
	serviceDialogueID: int

	def __init__(self, telegram_message_id: int, service_message_id: int, telegram_dialogue_id: int, service_dialogue_id: int, sent_via_telegram: bool) -> None:
		self.telegramMID = telegram_message_id
		self.serviceMID = service_message_id
		self.telegramDialogueID = telegram_dialogue_id
		self.serviceDialogueID = service_dialogue_id
		self.sentViaTelegram = sent_via_telegram
		self.sentViaService = not self.sentViaTelegram

class LatestMessage:
	"""
	Последнее сообщение диалога.
	"""

	telegram_message_id: int
	service_message_id: int

	def __init__(self, telegram_message_id: int, service_message_id: int) -> None:
		self.telegram_message_id = telegram_message_id
		self.service_message_id = service_message_id

class BaseTelehooperAPI:
	"""
	Базовый API для сервисов бота.
	"""

	available: bool
	serviceCodename: str

	telehooper_bot: "Telehooper"

	def __init__(self, telehooper_bot: "Telehooper") -> None:
		self.telehooper_bot = telehooper_bot

	async def onNewMessage(self, user: "TelehooperUser"):
		"""
		Вызывается при получении нового сообщения.
		"""

		self._checkAvailability()

	async def onNewIncomingMessage(self, user: "TelehooperUser"):
		"""
		Вызывается при получении нового входящего сообщения.
		"""

		self._checkAvailability()

	async def onNewOutcomingMessage(self, user: "TelehooperUser"):
		"""
		Вызывается при получении нового исходящего сообщения.
		"""

		self._checkAvailability()

	async def onMessageEdit(self, user: "TelehooperUser"):
		"""
		Вызывается при редактировании сообщения.
		"""

		self._checkAvailability()

	async def onMessageDelete(self, user: "TelehooperUser"):
		"""
		Вызывается при удалении сообщения (для всех).
		"""

	async def onSuccessfulConnection(self, user: "TelehooperUser"):
		"""
		Вызывается при успешном подключении сервиса.
		"""

		self._checkAvailability()

	async def onConnectionError(self, user: "TelehooperUser"):
		"""
		Вызывается в случае какой-либо ошибки. Например, если аккаунт был отключён со стороны сервиса.
		"""

		self._checkAvailability()

	async def onDisconnect(self, user: "TelehooperUser"):
		"""
		Вызывается в случае отключения сервиса.
		"""

		self._checkAvailability()

	async def onConvoAction(self, user: "TelehooperUser"):
		"""
		Вызывается при каком-либо специфичном для бесед событии, например, изменении имени или удаления участника.
		"""

		self._checkAvailability()

	async def reconnect(self, user: "TelehooperUser"):
		"""
		Вызывается для переподключения (восстановления сессии). Почти тоже самое что и `connect()`, но этот метод 'тише', поскольку ничего не отправляет пользователю.
		"""

		self._checkAvailability()

	async def onDialogueActivity(self, user: "TelehooperUser"):
		"""
		Вызывается, когда в диалоге происходит какое-нибудь событие, по типу "X печатает", "Y записывает голосовое сообщение", ...
		"""

		self._checkAvailability()

	async def connect(self, user: "TelehooperUser"):
		"""
		Подключает аккаунт сервиса к боту.
		"""

		self._checkAvailability()

	async def disconnect(self, user: "TelehooperUser"):
		"""
		Отключает аккаунт сервиса от бота.
		"""

		self._checkAvailability()

	async def sendMessage(self, user: "TelehooperUser"):
		"""
		Отправляет сообщение внутри сервиса.
		"""

		self._checkAvailability()

	async def startDialogueActivity(self, user: "TelehooperUser"):
		"""
		Начинает какое-либо действие в сервисе, например, печать, или запись голосового сообщения.
		"""

		self._checkAvailability()

	async def editMessage(self, user: "TelehooperUser"):
		"""
		Редактирует сообщение в сервисе.
		"""

		self._checkAvailability()

	async def deleteMessage(self, user: "TelehooperUser"):
		"""
		Удаляет сообщение сервиса.
		"""

		self._checkAvailability()

	async def markAsRead(self, user: "TelehooperUser"):
		"""
		Помечает сообщение как "прочитанное".
		"""

		self._checkAvailability()

	async def updatePin(self, user: "TelehooperUser"):
		"""
		Обновляет содержимое закреплённого сообщения с состоянием диалога.
		"""

		self._checkAvailability()

	def saveUserCache(self, service_name: str, user_id: int | str, data: dict, issued_by: int):
		"""
		Сохраняет информацию о пользователе в кэш.
		"""

		DB = getDefaultCollection()

		# Костыль. Проверяем, существует ли такой пользователь в кэше.
		# Если да, то мы извлекаем оттуда значение LastLookup.
		prevRes = DB.find_one(
			{
				"_id": "_global", 
				
				f"UsersCache.{service_name}.{user_id}": {
					"$exists": True
				}
			}
		)

		lastLookup = int(time.time())
		if prevRes:
			lastLookup = prevRes["UsersCache"][service_name][str(user_id)].get("LastLookup", int(time.time()))

		data.update({
			"LastLookup": lastLookup,
			"IssuedByTelegramID": issued_by
		})

		DB.update_one(
			{
				"_id": "_global"
			}, 
			
			{
				"$set": {
					f"UsersCache.{service_name}.{user_id}": data
				}
			}
		)

		return data

	def getUserCache(self, service_name: str, user_id: int | str, silent_lookup: bool = False):
		"""
		Достаёт информацию о пользователе из кэша.
		"""

		DB = getDefaultCollection()

		res = DB.find_one(
			{
				"_id": "_global"
			},

			{
				f"UsersCache.{service_name}.{user_id}": 1
			}
		)

		if not res:
			return None

		if not silent_lookup:
			DB.update_one(
				{
					"_id": "_global",
					f"UsersCache.{service_name}": str(user_id)
				},

				{
					"$set": {
						"LastLookup": int(time.time())
					}
				}
			)

		return res["UsersCache"][service_name].get(str(user_id))

	async def getBaseUserInfo(self, user: "TelehooperUser"):
		"""
		Достаёт базовую информацию о пользователе.
		"""

		self._checkAvailability()

	async def getBaseUserInfoMultiple(self, user: "TelehooperUser"):
		"""
		Достаёт базовую информацию о сразу нескольких пользователях.
		"""

		self._checkAvailability()

	async def ensureGetUserInfo(self, user: "TelehooperUser"):
		"""
		Достаёт информацию о пользователе из кэша. Если такого пользователя нет в кэше, то информация о нём принудительно скачивается.
		"""

		self._checkAvailability()

	def saveMessageID(self, user: "TelehooperUser", service_name: str, telegram_message_id: int | str, service_message_id: int | str, telegram_dialogue_id: int | str, service_dialogue_id: int | str, is_sent_via_telegram: bool) -> None:
		"""Сохраняет ID сообщения в базу."""

		DB = getDefaultCollection()

		DB.update_one({"_id": user.TGUser.id}, {
			"$push": {
				f"Services.{service_name}.ServiceToTelegramMIDs": {
					"TelegramMID": str(telegram_message_id),
					"ServiceMID": str(service_message_id),
					"TelegramDialogueID": str(telegram_dialogue_id),
					"ServiceDialogueID": str(service_dialogue_id),
					"ViaTelegram": is_sent_via_telegram
				}
			}
		})

	def runBackgroundTasks(self, loop: AbstractEventLoop):
		"""
		Создаёт фоновую задачу, ассоциированную с этим сервисом.
		"""

		self._checkAvailability()

	def getMessageDataByTelegramMID(self, user: "TelehooperUser", service_name: str, telegram_message_id: int | str) -> None | MappedMessage:
		return self._getMessageDataByKeyname(user, service_name, "TelegramMID", telegram_message_id)

	def getMessageDataByServiceMID(self, user: "TelehooperUser", service_name: str, service_message_id: int | str) -> None | MappedMessage:
		return self._getMessageDataByKeyname(user, service_name, "ServiceMID", service_message_id)

	def _getMessageDataByKeyname(self, user: "TelehooperUser", service_name: str, key: str, value: int | str):
		DB = getDefaultCollection()

		res = DB.find_one({"_id": user.TGUser.id})

		if not res:
			return None

		res = res["Services"][service_name]["ServiceToTelegramMIDs"]

		for r in res:
			if r[key] != str(value):
				continue

			TELEGRAMMID = int(r["TelegramMID"])
			SERVICEMID = int(r["ServiceMID"])
			TELEGRAMDIALOGUEID = int(r["TelegramDialogueID"])
			SERVICEDIALOGUEID = int(r["ServiceDialogueID"])
			VIATELEGRAM = bool(r["ViaTelegram"])

			return MappedMessage(TELEGRAMMID, SERVICEMID, TELEGRAMDIALOGUEID, SERVICEDIALOGUEID, VIATELEGRAM)

		return None

	def saveLatestMessageID(self, user: "TelehooperUser", service_name: str, dialogue_telegram_id: int | str, telegram_message_id: int | str, service_message_id: int | str) -> None:
		"""
		Сохраняет в ДБ ID последнего сообщения в диалоге.
		"""

		DB = getDefaultCollection()
		DB.update_one({"_id": "_global"}, {
			"$set": {
				f"ServiceDialogues.{service_name}.$[element].LatestMessageID": telegram_message_id,
				f"ServiceDialogues.{service_name}.$[element].LatestServiceMessageID": service_message_id
			}
		}, array_filters = [{"element.TelegramGroupID": dialogue_telegram_id}])

	def getLatestMessageID(self, user: "TelehooperUser", service_name: str, dialogue_telegram_id: int | str) -> LatestMessage | None:
		"""
		Возвращает ID последнего сообщения в диалоге.
		"""

		DB = getDefaultCollection()

		res = DB.find_one(
			{
				"_id": "_global", 
				f"ServiceDialogues.{service_name}.TelegramGroupID": int(dialogue_telegram_id)
			},

			{
				f"ServiceDialogues.{service_name}.$": 1, 
				"_id": 0
			}
		)
		if not res:
			return

		res = res["ServiceDialogues"][service_name][0]

		return LatestMessage(res["LatestMessageID"], res["LatestServiceMessageID"])

	async def getDialogueGroupByTelegramGroup(self, telegram_group: int) -> DialogueGroup | None:
		return await self.telehooper_bot.getDialogueGroupByTelegramGroup(telegram_group)

	async def getDialogueGroupByServiceDialogueID(self, service_dialogue_id: int, telegram_user_id: int) -> DialogueGroup | None:
		return await self.telehooper_bot.getDialogueGroupByServiceDialogueID(service_dialogue_id, telegram_user_id)

	def _checkAvailability(self):
		"""
		Проверяет, доступен ли сервис. Если нет, то вызывает `Exception`.
		"""

		if not self.available:
			raise Exception("This service is not available yet")

# coding: utf-8

"""
Базовый объект API. Все сервисы должны импортировать значения из данного базового класса.
"""

from typing import TYPE_CHECKING, Tuple, cast

import aiogram

from Consts import MAPIServiceType
from DB import getDefaultCollection

if TYPE_CHECKING:
	from TelegramBot import Telehooper, TelehooperUser
	from ServiceAPIs.VK import VKTelehooperAPI

class DialogueGroup:
	"""
	Класс, отображающий объект группы-диалога в Telegram.
	"""

	group: aiogram.types.Chat
	serviceType: int
	serviceDialogueID: int


	def __init__(self, group: aiogram.types.Chat, service_dialogue_id: int) -> None:
		self.group = group
		self.serviceType = MAPIServiceType.VK
		self.serviceDialogueID = service_dialogue_id

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

	def getLatestMessageID(self, user: "TelehooperUser", dialogue_telegram_id: int | str) -> Tuple[int, int] | None:
		"""
		Возвращает ID последнего сообщения в диалоге.
		"""

		# TODO
		# DB = getDefaultCollection()
		# # res = DB.find_one({"_id": "_global", "ServiceDialogues.VK.$[element].TelegramGroupID": dialogue_telegram_id}, array_filters=[{"element.TelegramGroupID": dialogue_telegram_id}])
		# res = DB.find_one({"_id": "_global", "ServiceDialogues.VK.TelegramGroupID": dialogue_telegram_id}, {"ServiceDialogues.VK.LatestServiceMessageID": 1, "ServiceDialogues.VK.LatestMessageID": 1, "ServiceDialogues.VK.TelegramGroupID": 1})

		# if res:
		# 	return res["ServiceDialogues"]["VK"][0]["LatestMessageID"], res["ServiceDialogues"]["VK"][0]["LatestServiceMessageID"]

		# return None

		pass

	async def getDialogueGroupByTelegramGroup(self, telegram_group: aiogram.types.Chat | int) -> DialogueGroup | None:
		return await self.telehooper_bot.getDialogueGroupByTelegramGroup(telegram_group)

	async def getDialogueGroupByServiceDialogueID(self, service_dialogue_id: aiogram.types.Chat | int) -> DialogueGroup | None:
		return await self.telehooper_bot.getDialogueGroupByServiceDialogueID(service_dialogue_id)

	def _checkAvailability(self):
		"""
		Проверяет, доступен ли сервис. Если нет, то вызывает `Exception`.
		"""

		if not self.available:
			raise Exception("This service is not available yet")

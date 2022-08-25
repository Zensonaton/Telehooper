# coding: utf-8

"""
Базовый объект API. Все сервисы должны импортировать значения из данного базового класса.
"""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
	from TelegramBot import TelehooperUser, Telehooper


class baseTelehooperAPI:
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

		raise Exception("Not implemented yet")

	async def onNewIncomingMessage(self, user: "TelehooperUser"):
		"""
		Вызывается при получении нового входящего сообщения.
		"""

		raise Exception("Not implemented yet")

	async def onNewOutcomingMessage(self, user: "TelehooperUser"):
		"""
		Вызывается при получении нового исходящего сообщения.
		"""

		raise Exception("Not implemented yet")

	async def onMessageEdit(self, user: "TelehooperUser"):
		"""
		Вызывается при редактировании сообщения.
		"""

		raise Exception("Not implemented yet")

	async def onSuccessfulConnection(self, user: "TelehooperUser"):
		"""
		Вызывается при успешном подключении сервиса.
		"""

		raise Exception("Not implemented yet")

	async def onConnectionError(self, user: "TelehooperUser"):
		"""
		Вызывается в случае какой-либо ошибки. Например, если аккаунт был отключён со стороны сервиса.
		"""

		raise Exception("Not implemented yet")

	async def onDisconnect(self, user: "TelehooperUser"):
		"""
		Вызывается в случае отключения сервиса.
		"""

		raise Exception("Not implemented yet")

	async def connect(self, user: "TelehooperUser"):
		"""
		Подключает аккаунт сервиса к боту.
		"""

		raise Exception("Not implemented yet")

	async def disconnect(self, user: "TelehooperUser"):
		"""
		Отключает аккаунт сервиса от бота.
		"""

		raise Exception("Not implemented yet")


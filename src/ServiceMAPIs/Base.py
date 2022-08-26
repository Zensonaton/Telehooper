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

	def _checkAvailability(self):
		"""
		Проверяет, доступен ли сервис. Если нет, то вызывает `Exception`.
		"""

		if not self.available:
			raise Exception("This service is not available yet")




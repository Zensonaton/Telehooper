# coding: utf-8

"""
Базовый объект API. Все сервисы должны импортировать значения из данного базового класса.
"""

class baseTelehooperAPI:
	"""
	Базовый API для сервисов бота.
	"""

	available: bool
	serviceCodename: str
	serviceName: str 

	def __init__(self) -> None:
		pass

	async def onNewMessage(self):
		"""
		Вызывается при получении нового сообщения.
		"""

		raise Exception("Not implemented yet")

	async def onNewIncomingMessage(self):
		"""
		Вызывается при получении нового входящего сообщения.
		"""

		raise Exception("Not implemented yet")

	async def onNewOutcomingMessage(self):
		"""
		Вызывается при получении нового исходящего сообщения.
		"""

		raise Exception("Not implemented yet")

	async def onMessageEdit(self):
		"""
		Вызывается при редактировании сообщения.
		"""

		raise Exception("Not implemented yet")

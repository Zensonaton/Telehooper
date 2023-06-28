# coding: utf-8

class BaseTelehooperServiceAPI:
	"""
	Базовый API для сервисов Telehooper.
	"""

	def __init__(self) -> None:
		"""
		Инициализирует данный Service API.
		"""

		pass

	async def start_listening(self) -> None:
		"""
		Запускает прослушивание событий с сервиса, т.е., получение сообщений.

		Данный метод обязан создавать и возвращать `asyncio.Task`, не останавливая обработку основного loop'а.
		"""

		raise NotImplementedError

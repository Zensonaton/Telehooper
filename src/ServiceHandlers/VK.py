# coding: utf-8

# Handler для ВКонтакте.


import asyncio
import logging

from vkbottle import VKAPIError

from MiddlewareAPI import MiddlewareAPI
from vkbottle.user import Message

logger = logging.getLogger(__name__)

class VKServiceHandler:
	"""
	ВК Handler для работы над сообщениями.
	"""

	mAPI: MiddlewareAPI
	pollingTask: asyncio.Task
	_pollingTaskIsCancelled: bool

	def __init__(self, middlewareAPI: MiddlewareAPI) -> None:
		self.mAPI = middlewareAPI

		self._pollingTaskIsCancelled = False

		self.mAPI.vkUser.on.message()(self.onMessage)

	def runPolling(self):
		"""
		Запуск поллинга.
		"""

		@self.mAPI.vkUser.error_handler.register_error_handler(VKAPIError[5])
		async def errorHandler(e: VKAPIError):
			# Если этот код вызывается, то значит, что пользователь отозвал разрешения ВК, и сессия была отозвана.


			# Это - костыль, созданный из за бага в библиотеке vkbottle.
			#
			# По непонятной мне причине, используя task.cancel()
			# всё ломается, и начинается бесконечный цикл 
			# из одной и той же ошибки, и поэтому мне пришлось
			# воспользоваться таким вот, не очень приятным, но
			# работающим вариантом отключения Task'а.
			#
			# Увы, но цикл всё равно остаётся работать в фоне,
			# хоть он и ничего не пишет и не делает.
			# Фиксится это только рестартом бота.
			# Ждём фикса! 
			#
			# Github Issue: https://github.com/vkbottle/vkbottle/issues/504
			if self._pollingTaskIsCancelled:
				return

			# Отправляем различные сообщения о отключённом боте:
			await self.mAPI.processServiceDisconnect(False)

			self._pollingTaskIsCancelled = True
			self.pollingTask.cancel()

		# Создаём Polling-задачу:
		self.pollingTask = asyncio.create_task(self.mAPI.vkUser.run_polling(), name=f"VK Polling, id{self.mAPI.vkFullUser.id}")


	async def onMessage(self, msg: Message):
		"""
		Обработчик входящих/исходящих сообщений.
		"""

		await self.mAPI.sendMessage(msg.text)

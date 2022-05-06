# coding: utf-8

# Handler для ВКонтакте.


import asyncio
import logging

from vkbottle import VKAPIError

from MiddlewareAPI import AccountDisconnectType, MiddlewareAPI
from vkbottle.user import Message

logger = logging.getLogger(__name__)

class VKServiceHandler:
	"""
	ВК Handler для работы над сообщениями.
	"""

	mAPI: MiddlewareAPI
	pollingTask: asyncio.Task

	def __init__(self, middlewareAPI: MiddlewareAPI) -> None:
		self.mAPI = middlewareAPI

		self.mAPI.vkUser.on.message()(self.onMessage)

	def runPolling(self):
		"""
		Запуск поллинга.
		"""

		@self.mAPI.vkUser.error_handler.register_error_handler(VKAPIError[5])
		async def errorHandler(e: VKAPIError):
			# Если этот код вызывается, то значит, что пользователь отозвал разрешения ВК, и сессия была отозвана.

			# Отправляем различные сообщения о отключённом боте:
			await self.mAPI.processServiceDisconnect(AccountDisconnectType.EXTERNAL)

			self.mAPI.vkUser.polling.stop = True # type: ignore

		# Создаём Polling-задачу:
		self.pollingTask = asyncio.create_task(self.mAPI.vkUser.run_polling(), name=f"VK Polling, id{self.mAPI.vkFullUser.id}")


	async def onMessage(self, msg: Message):
		"""
		Обработчик входящих/исходящих сообщений.
		"""

		await self.mAPI.sendMessage(msg.text)

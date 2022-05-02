# coding: utf-8

# Handler для ВКонтакте.


import logging
import asyncio
from vkbottle.user import Message
from MiddlewareAPI import MiddlewareAPI

logger = logging.getLogger(__name__)

class VKServiceHandler:
	"""
	ВК Handler для работы над сообщениями.
	"""

	mAPI: MiddlewareAPI

	def __init__(self, middlewareAPI: MiddlewareAPI) -> None:
		self.mAPI = middlewareAPI

		self.mAPI.vkUser.on.message()(self.onMessage)

		try:
			asyncio.create_task(self.mAPI.vkUser.run_polling(), name=f"VK Polling, id{self.mAPI.vkFullUser.id}")
		except:
			pass


	async def onMessage(self, msg: Message):
		"""
		Обработчик входящих/исходящих сообщений.
		"""

		await self.mAPI.sendMessage(msg.text)

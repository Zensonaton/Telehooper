# coding: utf-8

# Handler для ВКонтакте.


import aiogram
import vkbottle
import logging
import asyncio
from vkbottle.user import Message

logger = logging.getLogger(__name__)

class VKServiceHandler:
	"""
	ВК Handler для работы над сообщениями.
	"""

	vkUser: vkbottle.User
	telegramUser: aiogram.types.User


	def __init__(self, vkUser: vkbottle.User, telegramUser: aiogram.types.User) -> None:
		self.vkUser = vkUser
		self.telegramUser = telegramUser

		self.vkUser.on.message()(self.onMessage)

		asyncio.run_coroutine_threadsafe(vkUser.run_polling(), vkUser.loop)


	async def onMessage(self, msg: Message):
		"""
		Обработчик входящих/исходящих сообщений.
		"""

		logger.info(f"Сообщение {msg.text}")

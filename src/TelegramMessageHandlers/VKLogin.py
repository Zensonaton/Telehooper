# coding: utf-8

"""Handler для команды `VKLogin`."""

import logging

import Consts
import MiddleAPI
import vkbottle
from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `VKLogin`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(VKLogin, commands=["vklogin"])


async def VKLogin(msg: MessageType):
	args = (msg.get_args() or "").split(" ")

	if len(args) != 2:
		await msg.answer("Пожалуйста, используй команду в следующем формате для авторизации: <code>/vklogin логин пароль</code>.")

		return


	await msg.delete()
	await msg.answer("Прекрасно! Дай мне время, мне нужно проверить некоторые данные... ⏳\n\n<i>(твоё предыдущее сообщение было удалено в целях безопасности 👀)</i>")


	vkaccount: MiddleAPI.VKAccount
	try:
		vkToken = vkbottle.UserAuth(
			Consts.officialVKAppCreds.VK_ME.clientID,
			Consts.officialVKAppCreds.VK_ME.clientSecret
		)
		vkToken = await vkToken.get_token(
			args[0],
			args[1]
		)

		vkaccount = MiddleAPI.VKAccount(vkToken, msg.from_user, True)

		# Отправляем сообщения о подключении аккаунта...
		await vkaccount.postAuthInit()

		pass
	except Exception as error:
		logger.error(error)

		await msg.answer("Ошибка")


		

	
	

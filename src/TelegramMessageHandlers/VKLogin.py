# coding: utf-8

"""Handler для команды `VKLogin`."""

import logging

import Consts
import MiddlewareAPI
import vkbottle
from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from Consts import InlineButtonCallbacks as CButtons

BOT: Bot = None  # type: ignore
DP: Dispatcher = None # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `VKLogin`.
	"""

	global BOT, DP

	BOT = bot
	DP = dp
	dp.register_message_handler(VKLogin, commands=["vklogin"])


async def VKLogin(msg: MessageType):
	await DP.throttle("vklogin", rate=1)

	args = (msg.get_args() or "").split(" ")

	if len(args) != 2:
		await msg.answer("Пожалуйста, используй команду в следующем формате для авторизации: <code>/vklogin логин пароль</code>.")

		return


	await msg.delete()
	await msg.answer("Прекрасно! Дай мне время, мне нужно проверить некоторые данные... ⏳\n\n<i>(твоё предыдущее сообщение было удалено в целях безопасности 👀)</i>")


	vkaccount: MiddlewareAPI.VKAccount
	try:
		vkToken = vkbottle.UserAuth(
			Consts.officialVKAppCreds.VK_ME.clientID,
			Consts.officialVKAppCreds.VK_ME.clientSecret
		)
		vkToken = await vkToken.get_token(
			args[0],
			args[1]
		)

		vkaccount = MiddlewareAPI.VKAccount(vkToken, msg.from_user, True)

		# Отправляем сообщения о подключении аккаунта...
		await vkaccount.postAuthInit()
	except:
		keyboard = InlineKeyboardMarkup().add(
			InlineKeyboardButton(text="Авторизоваться через VK ID", callback_data=CButtons.VK_LOGIN_VIA_VKID)
		)

		await msg.answer("Упс, произошла ошибка при авторизации ВКонтакте. 😔\n\nВозможные причины:\n * пароль и/ли логин неверен; 🔐\n * бот столкнулся с проверкой Captcha; 🤖🔫\n * на твоём аккаунте подключена двухэтапная аутентификация, которая не поддерживается ботом. 🔑\n\nПопробуй снова; в случае дальнейших ошибок, воспользуйся авторизацией через VK ID, с которой намного меньше проблем:", reply_markup=keyboard)
	else:
		await msg.answer(f"Успех, я успешно подключился к твоей странице ВКонтакте. Приветствую тебя, <i>{vkaccount.vkFullUser.first_name} {vkaccount.vkFullUser.last_name}!</i> 😉👍")



		

	
	

# coding: utf-8

"""Handler для команды `VKLogin`."""

import logging

import Consts
import MiddlewareAPI
import vkbottle
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message as MessageType
from Consts import InlineButtonCallbacks as CButtons
from Consts import CommandThrottleNames as CThrottle
import Utils

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
	await DP.throttle(CThrottle.VK_LOGIN, rate=1)

	args = (msg.get_args() or "").split(" ")

	if len(args) != 2:
		await msg.answer("Пожалуйста, используй команду в следующем формате для авторизации: <code>/vklogin логин пароль</code>.")

		return


	await msg.delete()
	await msg.answer("Прекрасно! Дай мне время, мне нужно проверить некоторые данные... ⏳\n\n<i>(твоё предыдущее сообщение было удалено в целях безопасности 👀)</i>")


	vkAccount: MiddlewareAPI.VKAccount

	try:
		# Авторизуемся в ВК через логин+пароль:
		vkToken = await vkbottle.UserAuth(
			Consts.officialVKAppCreds.VK_ME.clientID,
			Consts.officialVKAppCreds.VK_ME.clientSecret
		).get_token(
			args[0],
			args[1]
		)

		# Создаём MAPI-объект:
		vkAccount = await MiddlewareAPI.MiddlewareAPI(
			msg.from_user
		).connectVKAccount(vkToken, True, True)

		# Отправляем различные сообщения о успешном подключении аккаунта:
		await vkAccount.postAuthInit()
	except:
		keyboard = InlineKeyboardMarkup().add(
			InlineKeyboardButton(text="Авторизоваться через VK ID", callback_data=CButtons.VK_LOGIN_VIA_VKID)
		)

		await msg.answer("Упс, произошла ошибка при авторизации ВКонтакте. 😔\n\nВозможные причины:\n * пароль и/ли логин неверен; 🔐\n * бот столкнулся с проверкой Captcha; 🤖🔫\n * на твоём аккаунте подключена двухэтапная аутентификация, которая не поддерживается ботом. 🔑\n\nПопробуй снова; в случае дальнейших ошибок, воспользуйся авторизацией через VK ID, с которой намного меньше проблем:", reply_markup=keyboard)
	else:
		await msg.answer(f"Успех, я успешно подключился к твоей странице ВКонтакте. Приветствую тебя, <i>{vkAccount.vkFullUser.first_name} {vkAccount.vkFullUser.last_name}!</i> 😉👍")

async def VKTokenMessageHandler(msg: MessageType):
	await DP.throttle(CThrottle.VK_LOGIN_VKID, rate=1)

	await msg.delete()
	await msg.answer("Прекрасно! Дай мне время, мне нужно проверить некоторые данные... ⏳\n\n<i>(твоё предыдущее сообщение было удалено в целях безопасности 👀)</i>")

	vkToken = Utils.extractAccessTokenFromFullURL(msg.text)
	vkaccount = await MiddlewareAPI.MiddlewareAPI(msg.from_user).connectVKAccount(vkToken, True, False)

	# Отправляем различные сообщения о успешном подключении аккаунта:
	await vkaccount.postAuthInit()

	await msg.answer(f"Успех, я успешно подключился к твоей странице ВКонтакте. Приветствую тебя, <i>{vkaccount.vkFullUser.first_name} {vkaccount.vkFullUser.last_name}!</i> 😉👍")

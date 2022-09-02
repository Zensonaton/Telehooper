# coding: utf-8

"""Обработчик для команды `VKLogin`."""

from __future__ import annotations
import asyncio

from typing import TYPE_CHECKING, cast

import Consts
import Utils
import vkbottle
from aiogram import Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message as MessageType
from aiogram.types import InputFile
from Consts import AccountDisconnectType
from Consts import CommandThrottleNames as CThrottle
from Consts import InlineButtonCallbacks as CButtons
from loguru import logger
from ServiceAPIs.VK import VKTelehooperAPI
from TelegramBot import TelehooperAPIStorage

if TYPE_CHECKING:
	from TelegramBot import Telehooper, TelehooperUser

TELEHOOPER:	Telehooper = None # type: ignore
DP: 		Dispatcher = None # type: ignore


def _setupHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global TELEHOOPER, DP

	TELEHOOPER = bot
	DP = TELEHOOPER.DP

	DP.register_message_handler(VKLogin, commands=["vklogin"])
	DP.register_message_handler(VKTokenMessageHandler, lambda msg: msg.text.startswith("https://oauth.vk.com/blank.html#access_token="))
	DP.register_message_handler(VKTokenURLMessageHandler, lambda msg: msg.text.strip().startswith("https://oauth.vk.com/authorize?client_id=2685278"))


async def VKLogin(msg: MessageType) -> None:
	await DP.throttle(CThrottle.VK_LOGIN, rate=1, chat_id=msg.chat.id)
	TELEHOOPER.vkAPI = cast("VKTelehooperAPI", TELEHOOPER.vkAPI)

	args = (msg.get_args() or "").split(" ")

	await msg.delete()

	# Проверяем количество аргументов:
	if len(args) != 2:
		await msg.answer("<b>Что-то пошло не так 😕\n\n</b>Я не смог понять, где именно у тебя <b>логин</b>, а где - <b>пароль</b>.\nПожалуйста, пользуйся командой в следующем формате: <code>/vklogin логин пароль</code>, например: <code>/vklogin 77771234567 password</code>")

		return

	# Забавная пасхалка:
	if args == ["paveldurovv", "tgisbetter"]:
		await msg.answer("<b>Что-то пошло не так 😅</b>\n\nТы не очень похож на Павла Дурова.")

		return

	# Получаем объект пользователя:
	user = await TELEHOOPER.getBotUser(msg.from_user.id)

	# Отправляем сообщения-статус:
	await msg.answer(
		"<b>Подключение аккаунта 🔗\n\n</b>Отлично, я получил всё необходимое для авторизации. Учти, что твоя предыдущая страница «ВКонтакте» будет отключена от бота. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n\n⏳ Теперь мне нужно немного времени..."
		if user.isVKConnected else
		"<b>Подключение аккаунта 🔗\n\n</b>Отлично, я получил всё необходимое для авторизации. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n\n⏳ Теперь мне нужно немного времени..."
	)

	# Мы не можем позволить пользователю подключить сразу 2 страницы ВКонтакте:
	if user.isVKConnected:
		await TELEHOOPER.vkAPI.disconnect(user, AccountDisconnectType.SILENT)

	try:
		# Авторизуемся в ВК через логин+пароль:
		vkToken = await vkbottle.UserAuth(
			Consts.officialVKAppCreds.VK_ME.clientID,
			Consts.officialVKAppCreds.VK_ME.clientSecret
		).get_token(
			args[0],
			args[1]
		)

		# Подключаем страницу ВК:
		await TELEHOOPER.vkAPI.connect(user, vkToken, True, True)
	except:
		# Что-то пошло не так, и мы не сумели авторизоваться.

		keyboard = InlineKeyboardMarkup().add(
			InlineKeyboardButton(text="🔑 Авторизоваться через VK ID", callback_data=CButtons.CommandMenus.VK_LOGIN_VKID)
		)

		await msg.answer("<b>Что-то пошло не так 😕\n\n</b>Я не сумел авторизоваться в твой аккаунт ВКонтакте. Возможные причины:\n    <b>•</b> Пароль и/ли логин неверен. 🔐\n    <b>•</b> К твоей странице подключена неподдерживаемая ботом двухэтапная аутентификация (2FA). 🔑\n    <b>•</b> Бот столкнулся с проверкой CAPTCHA. 🤖🔫\n\nПопробуй снова! Если снова не выйдет, то воспользуйся авторизацией через VK ID, ведь с ней намного меньше проблем.\n\n\n⚙️ Попробуй авторизоваться снова используя команду /vklogin, либо же авторизуйся через VK ID:", reply_markup=keyboard)
	else:
		# Всё ок, мы успешно авторизовались!
		# Отправляем сообщения о успешной авторизации пользователю.

		await successConnectionMessage(msg, user)

async def VKTokenMessageHandler(msg: MessageType):
	await DP.throttle(CThrottle.VK_LOGIN_VKID, rate=1, chat_id=msg.chat.id)

	await msg.delete()

	vkToken = Utils.extractAccessTokenFromFullURL(msg.text)

	# Получаем объект пользователя:
	user = await TELEHOOPER.getBotUser(msg.from_user.id)

	# Отправляем сообщения-статус:
	await msg.answer(
		"<b>Подключение аккаунта 🔗\n\n</b>Отлично, я получил всё необходимое для авторизации. Учти, что твоя предыдущая страница «ВКонтакте» будет отключена от бота. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n\n⏳ Теперь мне нужно немного времени..."
		if user.isVKConnected else
		"<b>Подключение аккаунта 🔗\n\n</b>Отлично, я получил всё необходимое для авторизации. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n\n⏳ Теперь мне нужно немного времени..."
	)

	# Мы не можем позволить пользователю подключить сразу 2 страницы ВКонтакте:
	if user.isVKConnected:
		TELEHOOPER.vkAPI = cast(VKTelehooperAPI, TELEHOOPER.vkAPI)
		await TELEHOOPER.vkAPI.disconnect(user, AccountDisconnectType.SILENT)
		await asyncio.sleep(1)

	# Подключаем аккаунт к боту:
	vkAccount = await TELEHOOPER.vkAPI.connect(user, vkToken, False, True) # type: ignore

	# Отправляем сообщения о успехе в самом Telegram пользователю:
	return await successConnectionMessage(msg, user)

async def successConnectionMessage(msg: MessageType, user: "TelehooperUser") -> MessageType:
	"""
	Отправляет сообщение в Telegram о успешном подключении аккаунта ВКонтакте.
	"""

	user.APIstorage.vk = cast("TelehooperAPIStorage.VKAPIStorage", user.APIstorage.vk)
	return await msg.answer_photo(
		InputFile.from_url(user.APIstorage.vk.fullUserInfo.photo_max_orig),
		f"<b>Подключение аккаунта 🔗\n\n</b>С радостью заявляю, что я сумел успешно подключиться к твоему аккаунту <b>ВКонтакте</b>!\nРад познакомиться, <b>{user.APIstorage.vk.accountInfo.first_name} {user.APIstorage.vk.accountInfo.last_name}</b>! 🙃👍\n\nТеперь, после подключения страницы ВКонтакте тебе нужно создать отдельную группу под каждый нужный тебе диалог ВКонтакте. Подробный гайд есть в команде /help.\nУправлять подключённой страницей ты можешь используя команду /me."
	)

async def VKTokenURLMessageHandler(msg: MessageType) -> MessageType:
	"""
	Отправляет сообщение в Telegram когда пользователь по-ошибке отправляет не тот URL.
	"""

	return await msg.answer("<b>Что-то пошло не так 😕\n\n</b>Ты мне отправил ссылку на страницу, <b>на которой нужно пройти авторизацию ВКонтакте</b>, и на странице <i>«не копируйте, вы можете потерять доступ к аккаунту ...»</i> скопировать текст с адресной строки браузера.\n<b>Попробуй снова!</b>")

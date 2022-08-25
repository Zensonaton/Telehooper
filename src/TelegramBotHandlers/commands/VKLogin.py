# coding: utf-8

"""Обработчик для команды `VKLogin`."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import Consts
import Utils
import vkbottle
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message as MessageType
from Consts import CommandThrottleNames as CThrottle
from Consts import InlineButtonCallbacks as CButtons

if TYPE_CHECKING:
	from TelegramBot import Telehooper

TelehooperBot: 	"Telehooper" 	= None # type: ignore
TGBot: 			Bot 		= None # type: ignore
DP: 			Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: "Telehooper") -> None:
	"""
	Инициализирует команду `VKLogin`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(VKLogin, commands=["vklogin"])
	DP.register_message_handler(VKTokenMessageHandler, lambda msg: msg.text.startswith("https://oauth.vk.com/blank.html#access_token="))
	DP.register_message_handler(VKTokenURLMessageHandler, lambda msg: msg.text.strip().startswith("https://oauth.vk.com/oauth/authorize?client_id=6463690"))


async def VKLogin(msg: MessageType) -> None:
	await DP.throttle(CThrottle.VK_LOGIN, rate=1, chat_id=msg.chat.id)

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
	user = await TelehooperBot.getBotUser(msg.from_user.id)

	# Отправляем сообщения-статус:
	await msg.answer(
		"<b>Подключение аккаунта 🔗\n\n</b>Отлично, я получил всё необходимое для авторизации. Учти, что твоя предыдущая страница «ВКонтакте» будет отключена от бота. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n\n⏳ Теперь мне нужно немного времени..."
		if user.isVKConnected else
		"<b>Подключение аккаунта 🔗\n\n</b>Отлично, я получил всё необходимое для авторизации. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n\n⏳ Теперь мне нужно немного времени..."
	)

	# Мы не можем позволить пользователю подключить сразу 2 страницы ВКонтакте:
	# if user.isVKConnected:
	# 	await user.vkMAPI.disconnectService(AccountDisconnectType.SILENT, True)

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
		vkAccount = await TelehooperBot.vkAPI.connect(user, vkToken, True, True) # type: ignore

	except:
		# Что-то пошло не так, и мы не сумели авторизоваться.

		keyboard = InlineKeyboardMarkup().add(
			InlineKeyboardButton(text="🔑 Авторизоваться через VK ID", callback_data=CButtons.CommandMenus.VK_LOGIN_VKID)
		)

		await msg.answer("<b>Что-то пошло не так 😕\n\n</b>Я не сумел авторизоваться в твой аккаунт ВКонтакте. Возможные причины:\n    <b>•</b> Пароль и/ли логин неверен. 🔐\n    <b>•</b> К твоей странице подключена неподдерживаемая ботом двухэтапная аутентификация (2FA). 🔑\n    <b>•</b> Бот столкнулся с проверкой CAPTCHA. 🤖🔫\n\nПопробуй снова! Если снова не выйдет, то воспользуйся авторизацией через VK ID, ведь с ней намного меньше проблем.\n\n\n⚙️ Попробуй авторизоваться снова используя команду /vklogin, либо же авторизуйся через VK ID:", reply_markup=keyboard)
	else:
		# Всё ок, мы успешно авторизовались!
		pass

		# await successConnectionMessage(msg, vkAccount)

async def VKTokenMessageHandler(msg: MessageType):
	await DP.throttle(CThrottle.VK_LOGIN_VKID, rate=1, chat_id=msg.chat.id)

	await msg.delete()

	vkToken = Utils.extractAccessTokenFromFullURL(msg.text)

	# Получаем объект пользователя:
	user = await TelehooperBot.getBotUser(msg.from_user.id)

	# Отправляем сообщения-статус:
	await msg.answer(
		"<b>Подключение аккаунта 🔗\n\n</b>Отлично, я получил всё необходимое для авторизации. Учти, что твоя предыдущая страница «ВКонтакте» будет отключена от бота. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n\n⏳ Теперь мне нужно немного времени..."
		if user.isVKConnected else
		"<b>Подключение аккаунта 🔗\n\n</b>Отлично, я получил всё необходимое для авторизации. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n\n⏳ Теперь мне нужно немного времени..."
	)

	# Мы не можем позволить пользователю подключить сразу 2 страницы ВКонтакте:
	# if user.isVKConnected:
	# 	await user.vkMAPI.disconnectService(AccountDisconnectType.SILENT, True)

	# Подключаем аккаунт к боту:
	# vkAccount = await user.connectVKAccount(vkToken, False)
	vkAccount = await TelehooperBot.vkAPI.connect(user, vkToken, False, True) # type: ignore

	# Отправляем различные сообщения о успешном подключении аккаунта:
	# await vkAccount.postAuthInit()

	# Отправляем сообщения о успехе в самом Telegra    m, пользователю:
	# return await successConnectionMessage(msg, vkAccount)

async def successConnectionMessage(msg: MessageType, vkAccount) -> MessageType:
	return await msg.answer(f"<b>Подключение аккаунта 🔗\n\n</b>С радостью заявляю, что я сумел успешно подключиться к твоему аккаунту <b>ВКонтакте</b>!\nРад тебя видеть, <b>{vkAccount.vkFullUser.first_name} {vkAccount.vkFullUser.last_name}</b>! 🙃👍\n\nТеперь, после подключения страницы ВКонтакте тебе нужно создать отдельную группу под каждый нужный тебе диалог ВКонтакте. Подробный гайд есть в команде /help.\nУправлять подключённой страницей ты можешь используя команду /self.")

async def VKTokenURLMessageHandler(msg: MessageType) -> MessageType:
	return await msg.answer("<b>Что-то пошло не так 😕\n\n</b>Ты мне отправил ссылку на страницу, на которой нужно пройти авторизацию ВКонтакте, и на странице <i>«не копируйте, вы можете потерять доступ к аккаунту ...»</i> скопировать текст с адресной строки браузера.\n<b>Попробуй снова!</b>")

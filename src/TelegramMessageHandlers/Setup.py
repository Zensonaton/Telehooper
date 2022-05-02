# coding: utf-8

"""Handler для команды `Setup`."""

import logging

import MiddleAPI
import Utils
from aiogram import Bot, Dispatcher
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from aiogram.types import Message as MessageType
from Consts import InlineButtonCallbacks as CButtons

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `Setup`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(Setup, commands=["setup"])
	dp.register_callback_query_handler(SetupCallbackHandler, lambda query: query.data in [CButtons.ADD_VK_ACCOUNT, CButtons.VK_LOGIN_VIA_PASSWORD, CButtons.VK_LOGIN_VIA_VKID, CButtons.BACK_TO_SERVICE_SELECTOR])
	dp.register_message_handler(VKTokenMessageHandler, lambda msg: msg.text.startswith("https://oauth.vk.com/blank.html#access_token="))


async def Setup(msg: MessageType):
	await SetupMessage(msg)

async def SetupMessage(msg: MessageType, edit_message_instead: bool = False):
	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton(text="ВКонтакте", callback_data=CButtons.ADD_VK_ACCOUNT),
	)

	_text = "Выбери нужный тебе сервис, который необходимо подключить к боту. В данный момент поддерживается лишь <b>ВКонтакте</b>, однако, в будущем планируется больше!\nЕсли у тебя есть знания Python и ты хочешь помочь, то дорога в <a href=\"https://github.com/Zensonaton/Telehooper\">Github проекта</a> открыта! 👀\n\n⚙️ Выбери сервис:"

	if edit_message_instead:
		await msg.edit_text(_text, reply_markup=keyboard)
		return

	await msg.answer(_text, reply_markup=keyboard)


async def SetupCallbackHandler(query: CallbackQuery):
	"""В этом Callback Handler'е вызываются остальные функции для авторизации."""

	if query.data == CButtons.ADD_VK_ACCOUNT:
		keyboard = InlineKeyboardMarkup(
			row_width=2
		).add(
			InlineKeyboardButton(text="VK ID", callback_data=CButtons.VK_LOGIN_VIA_VKID),
			InlineKeyboardButton(text="Пароль", callback_data=CButtons.VK_LOGIN_VIA_PASSWORD),
		).add(
			InlineKeyboardButton(text="🔙 Назад", callback_data=CButtons.BACK_TO_SERVICE_SELECTOR),
		)

		await query.message.edit_text("Прекрасно, ты выбрал <b>«ВКонтакте»</b> для подключения, и теперь тебе необходимо авторизоваться в эту социальную сеть, что бы продолжить. Авторизоваться можно сделать двумя методами:\n<b>1</b>. Используя «официальный» метод; авторизоваться, используя окно подключения VK ID. <b><i>(рекомендуется)</i></b>\n<b>2</b>. Введя логин и пароль сюда. <b>НЕ РЕКОМЕНДУЕТСЯ</b>, этот метод менее безопасен, а так же страницы с двухэтапной аутентификацией не работают через этот метод.\n\n⚙️ Какой метод авторизации тебе предпочтительнее?", reply_markup=keyboard)
	elif query.data == CButtons.BACK_TO_SERVICE_SELECTOR:
		await SetupMessage(query.message, True)
	elif query.data == CButtons.VK_LOGIN_VIA_VKID:
		# TODO: Реализовать настройку, что бы бот мог хостить Flask приложение, и если бот настроен на это, то вместо редиректа на blank использовать Flask-приложение.
		auth_url = f"https://oauth.vk.com/authorize?client_id=6463690&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1"

		keyboard = InlineKeyboardMarkup().add(
			InlineKeyboardButton(text="Авторизоваться", url=auth_url),
		).add(
			InlineKeyboardButton(text="🔙 Назад", callback_data=CButtons.ADD_VK_ACCOUNT),
		)

		await query.message.edit_text(f"Отлично! Перейди по <a href=\"{auth_url}\">вот этой ссылке</a>, авторизуйся там.\nК сожалению, ввиду технических ограничений ВКонтакте, авторизация производится через приложение «Маруся».\n<b>После авторизации во ВКонтакте, отправь адресную ссылку <i>(URL)</i> сюда.</b>", reply_markup=keyboard)
	elif query.data == CButtons.VK_LOGIN_VIA_PASSWORD:
		await query.message.edit_text("Напиши логин и пароль в отдельном сообщении, в следующем формате: <code>/vklogin логин пароль</code>, пример: \n<code>/vklogin vasyapupkin 123456password</code>\n\n⚙️ Введи логин и пароль в одном сообщении:")
	else:
		print("UNKNOWN", query.data)

	await query.answer()

async def VKTokenMessageHandler(msg: MessageType):
	await msg.delete()
	await msg.answer("Прекрасно! Дай мне время, мне нужно проверить некоторые данные... ⏳\n\n<i>(твоё предыдущее сообщение было удалено в целях безопасности 👀)</i>")

	vkToken = Utils.extractAccessTokenFromFullURL(msg.text)
	vkaccount = MiddleAPI.VKAccount(vkToken, msg.from_user, False)

	# Отправляем сообщения о подключении аккаунта...
	await vkaccount.postAuthInit()

	await msg.answer(f"Успех, я успешно подключился к твоей странице ВКонтакте. Приветствую тебя, <i>{vkaccount.vkUser.first_name} {vkaccount.vkUser.last_name}!</i> 😉👍")

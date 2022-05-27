# coding: utf-8

"""Обработчик для команды `Self`."""

import logging

import MiddlewareAPI
from aiogram import Bot, Dispatcher
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from aiogram.types import Message as MessageType
from Consts import AccountDisconnectType
from Consts import CommandThrottleNames as CThrottle
from Consts import InlineButtonCallbacks as CButtons
from Consts import MAPIServiceType
from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `Self`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(Self, commands=["self", "me", "myself", "profile", "service"])
	DP.register_callback_query_handler(SelfCallbackHandler, lambda query: query.data in [CButtons.DISCONNECT_SERVICE])


async def Self(msg: MessageType):
	await DP.throttle(CThrottle.SERVICES_LIST, rate=2, user_id=msg.from_user.id)

	# Получаем объект пользователя:
	user = await Bot.getBotUser(msg.from_user.id)

	if not user.isVKConnected:
		await msg.answer("😔 Извини, но у тебя ещё нет ни одного подключённого сервиса.\n\n⚙️ Воспользуйся командой /setup для подключения!")
		return

	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton(text="🛑 Отключить сервис", callback_data=CButtons.DISCONNECT_SERVICE),
	)
	await msg.answer("В данный момент, у тебя есть подключённый сервис, <b>ВКонтакте</b>. Что ты хочешь с ним сделать?\n\n⚙️ Выбери действие над сервисом «ВКонтакте»:", reply_markup=keyboard)

async def SelfCallbackHandler(query: CallbackQuery):
	# Получаем объект пользователя:
	user = await Bot.getBotUser(query.from_user.id)

	if query.data == CButtons.DISCONNECT_SERVICE:
		await user.vkMAPI.disconnectService(AccountDisconnectType.INITIATED_BY_USER, True)


	await query.answer()

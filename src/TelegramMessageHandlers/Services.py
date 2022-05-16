# coding: utf-8

"""Handler для команды `Services`."""

from aiogram.types import Message as MessageType
from aiogram import Dispatcher, Bot
import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from Consts import AccountDisconnectType, InlineButtonCallbacks as CButtons, MAPIServiceType, CommandThrottleNames as CThrottle

import MiddlewareAPI

BOT: Bot = None  # type: ignore
DP: Dispatcher = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `Services`.
	"""

	global BOT, DP

	BOT = bot
	DP = dp
	dp.register_message_handler(Services, commands=["services"])
	dp.register_callback_query_handler(ServicesCallbackHandler, lambda query: query.data in [CButtons.DISCONNECT_SERVICE])


async def Services(msg: MessageType):
	await DP.throttle(CThrottle.SERVICES_LIST, rate=2, user_id=msg.from_user.id)

	mAPI = MiddlewareAPI.MiddlewareAPI(msg.from_user)
	await mAPI.restoreFromDB()

	if not mAPI.isVKConnected:
		await msg.answer("😔 Извини, но у тебя ещё нет ни одного подключённого сервиса.\n\n⚙️ Воспользуйся командой /setup для подключения!")
		return

	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton(text="🛑 Отключить сервис", callback_data=CButtons.DISCONNECT_SERVICE),
	)
	await msg.answer("В данный момент, у тебя есть подключённый сервис, <b>ВКонтакте</b>. Что ты хочешь с ним сделать?\n\n⚙️ Выбери действие над сервисом «ВКонтакте»:", reply_markup=keyboard)

async def ServicesCallbackHandler(query: CallbackQuery):
	mAPI = MiddlewareAPI.MiddlewareAPI(query.from_user)
	await mAPI.restoreFromDB()

	if query.data == CButtons.DISCONNECT_SERVICE:
		await mAPI.processServiceDisconnect(MAPIServiceType.VK, AccountDisconnectType.INITIATED_BY_USER, True)


	await query.answer()

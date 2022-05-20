# coding: utf-8

"""Обработчик для команды `ConvertToPublicServiceDialogue`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message as MessageType
from Consts import InlineButtonCallbacks as CButtons
from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `ConvertToPublicServiceDialogue`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(ConvertToPublicServiceDialogue, commands=["converttopublicservicedialogue"])


async def ConvertToPublicServiceDialogue(msg: MessageType) -> None:
	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton("Отменить", callback_data=CButtons.CANCEL_GROUP_TRANSFORM)
	)

	await msg.reply("""<b>⚠️ Внимание! Опасная команда! ⚠️</b>

Ты прописал опасную команду. Данная команда преобразует обычную группу в «<b><u>публичную</u> служебную группу</b>», то есть в группу для получения сообщений из подключённых в боте сервисов.
<b><u>Если ты покинешь эту группу, то</u></b>:
 • Эта группа будет зарезервирована ботом, и дальше любой пользователь бота сумеет воспользоваться ею.

Действие перевода в «сервисную группу» <b>возможно отменить</b>, если нажать на кнопку ниже. В ином случае, <b>после выхода из группы произойдёт то, что описано выше</b>.""", reply_markup=keyboard)

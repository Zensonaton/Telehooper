# coding: utf-8

"""Обработчик для команды `Help`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `Help`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(Help, commands=["help"])


async def Help(msg: MessageType) -> None:
	await msg.answer("<b>Помощь по боту</b> ℹ️\n\nУ меня есть лишь несколько, относящихся к работе самого бота:\n    <b>•</b> /self — информация о текущих <b>подключённых к боту сервисов</b>, а так же <b>управление ими</b>.\n    <b>•</b> /this — информация о текущей <b>группе</b>. Команда нужна для создания <b>диалогов</b> и <b>управления ими</b>.\n\nУ бота есть открытый исходный код на <a href=\"https://github.com/Zensonaton/Telehooper\">Github</a>. Столкнувшись с каким либо багом, или умной идеей в голове смело создавай issue.")

# coding: utf-8

"""Обработчик для команды `Help`."""

from aiogram import Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger
from TelegramBot import Telehooper

TELEHOOPER:	Telehooper = None # type: ignore
DP: 		Dispatcher = None # type: ignore


def _setupHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global TELEHOOPER, DP

	TELEHOOPER = bot
	DP = TELEHOOPER.DP

	DP.register_message_handler(Help, commands=["help"])


async def Help(msg: MessageType) -> None:
	await msg.answer("<b>Помощь по боту</b> ℹ️\n\nУ меня есть лишь несколько, относящихся к работе самого бота:\n    <b>•</b> /self — информация о текущих <b>подключённых к боту сервисов</b>, а так же <b>управление ими</b>.\n    <b>•</b> /this — информация о текущей <b>группе</b>. Команда нужна для создания <b>диалогов</b> и <b>управления ими</b>.\n\nУ бота есть открытый исходный код на <a href=\"https://github.com/Zensonaton/Telehooper\">Github</a>. Столкнувшись с каким либо багом, или умной идеей в голове смело создавай issue.")

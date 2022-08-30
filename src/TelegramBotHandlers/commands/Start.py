# coding: utf-8

"""Обработчик для команды `Start`."""

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

	DP.register_message_handler(Start, commands=["start"])


async def Start(msg: MessageType) -> None:
	await msg.answer("<b>Привет! 🙋\n\n</b>Я — бот с <a href=\"https://github.com/Zensonaton/Telehooper\">открытым исходным кодом</a>, позволяющий <b>отправлять</b> и <b>получать</b> сообщения из <b>ВКонтакте</b> напрямую в Telegram. 🤖\n\n⚙️ Для продолжения воспользуйся командой /self.")

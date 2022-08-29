# coding: utf-8

"""Обработчик для команды `Settings`."""

from typing import TYPE_CHECKING

import aiogram
from aiogram import Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger

if TYPE_CHECKING:
	from TelegramBot import Telehooper

Bot: 	"Telehooper" 	= None # type: ignore
TGBot:	aiogram.Bot 	= None # type: ignore
DP: 	Dispatcher 		= None # type: ignore


def _setupCHandler(bot: "Telehooper") -> None:
	"""
	Инициализирует команду `Settings`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(Settings, commands=["settings", "options", "setting", "option"])

async def Settings(msg: MessageType) -> None:
	await msg.answer("""<b>Настройки ⚙️</b>
	
	Для навигации по этому меню используй <b>кнопки</b> под этим сообщением.\nНавигайся по разным <b>«разделам»</b> настроек, отмеченных эмодзи 📁, редактируй <b>индивидуальные настройки</b> внутри этих «разделов», что отмечены эмодзи ⚙️.
	
	<code>
	📂 Настройки
	 ├─ 📁 визуальное
	 ├─ 📁 безопасность
	 ├─ 📁 сервисы
	 └─ 📁 другое
	</code>""")

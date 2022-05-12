# coding: utf-8

"""Handler для команды `ConvertToPublicServiceDialogue`."""

from aiogram.types import Message as MessageType, InlineKeyboardButton, InlineKeyboardMarkup
from Consts import InlineButtonCallbacks as CButtons
from aiogram import Dispatcher, Bot
import logging

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `ConvertToPublicServiceDialogue`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(ConvertToPublicServiceDialogue, commands=["converttopublicservicedialogue"])


async def ConvertToPublicServiceDialogue(msg: MessageType):
	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton("Отменить", callback_data=CButtons.CANCEL_GROUP_TRANSFORM)
	)

	await msg.reply("""<b>⚠️ Внимание! Опасная команда! ⚠️</b>

Ты прописал опасную команду. Данная команда преобразует обычную группу в «<b><u>публичную</u> служебную группу</b>», то есть в группу для получения сообщений из подключённых в боте сервисов.
<b><u>Если ты покинешь эту группу, то</u></b>:
 <b>*</b> Эта группа будет зарезервирована ботом, и дальше любой пользователь бота сумеет воспользоваться ею.

Действие перевода в «сервисную группу» <b>возможно отменить</b>, если нажать на кнопку ниже. В ином случае, <b>после выхода из группы произойдёт то, что описано выше</b>.""", reply_markup=keyboard)

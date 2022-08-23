# coding: utf-8

"""Обработчик для команды `GroupEvents`."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from TelegramBot import Telehooper

TelehooperBot: 	Telehooper 	= None # type: ignore
TGBot: 			Bot 		= None # type: ignore
DP: 			Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `GroupEvents`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_chat_join_request_handler(GroupJoinHandler)
	DP.register_message_handler(GroupJoinHandler, content_types=["new_chat_members", "group_chat_created", "supergroup_chat_created"])


async def GroupJoinHandler(msg: MessageType) -> None:
	bot_id = (await TGBot.get_me()).id

	if not ((msg.content_type != "new_chat_members") or ([i for i in msg.new_chat_members if i.id == bot_id] and msg.content_type == "new_chat_members")):
		# В группу добавили кого-то другого, а не бота,
		# Либо же это было не событие добавления бота в беседу.

		return

	await msg.answer("<b>Группа-диалог 🫂\n\n</b>Прекрасно, ведь теперь, после добавления меня в группу ты можешь преобразовать её в <b>«диалог»</b>, и все сообщения с определённого диалога сервиса будут появляться именно здесь. \nК примеру, если выбрать <a href=\"http://vk.com/durov\">Павла Дурова</a>, то все его новые сообщения будут <b>появляться здесь</b>, и на них ты сумеешь <b>отвечать</b> тут же. Технологии! 👨‍💻\n\n⚙️ Используй команду /this для продолжения.")

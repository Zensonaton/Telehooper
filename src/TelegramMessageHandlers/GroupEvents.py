# coding: utf-8

"""Handler для команды `GroupEvents`."""

from aiogram.types import Message as MessageType
from aiogram import Dispatcher, Bot
import logging

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `GroupEvents`.
	"""

	global BOT

	BOT = bot
	dp.register_chat_join_request_handler(GroupJoinHandler)
	dp.register_message_handler(GroupJoinHandler, content_types=["new_chat_members", "group_chat_created", "supergroup_chat_created"])


async def GroupJoinHandler(msg: MessageType):
	bot_id = (await BOT.get_me()).id

	if not ((msg.content_type != "new_chat_members") or ([i for i in msg.new_chat_members if i.id == bot_id] and msg.content_type == "new_chat_members")):
		# В группу добавили кого-то другого, а не бота,
		# Либо же это было не событие добавления бота в беседу.

		return

	await msg.answer("Меня добавили в супер-группу! Ура!")


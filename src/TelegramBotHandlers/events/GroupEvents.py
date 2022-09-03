# coding: utf-8

"""Обработчик для команды `GroupEvents`."""

from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.types import Message as MessageType
from loguru import logger
from TelegramBot import Telehooper

if TYPE_CHECKING:
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

	DP.register_chat_join_request_handler(GroupJoinHandler)
	DP.register_message_handler(GroupJoinHandler, content_types=["new_chat_members", "group_chat_created", "supergroup_chat_created"])


async def GroupJoinHandler(msg: MessageType) -> None:
	bot_id = (await TELEHOOPER.TGBot.get_me()).id

	if ([i for i in msg.new_chat_members if i.id == bot_id]):
		# Добавили текущего бота в беседу.

		await msg.answer("<b>Группа-диалог 🫂\n\n</b>Прекрасно, ведь теперь, после добавления меня в группу ты можешь преобразовать её в <b>«диалог»</b>, и все сообщения с определённого диалога сервиса будут появляться именно здесь. \nК примеру, если выбрать <a href=\"http://vk.com/durov\">Павла Дурова</a>, то все его новые сообщения будут <b>появляться здесь</b>, и на них ты сумеешь <b>отвечать</b> тут же. Технологии! 👨‍💻\n\n⚙️ Используй команду /this для продолжения.", disable_web_page_preview=True)

		return

	# Иной случай, добавили кого-то иного в группу:

	await msg.answer("<b>Группа-диалог 🫂\n\n</b>Ты добавил другого пользователя в группу-диалог. Это не запрещено ботом, но это <b>не рекомендуется</b>, поскольку есть <b>риск утечки секретных данных</b>.\n\nБудь осторожен! 🙈")

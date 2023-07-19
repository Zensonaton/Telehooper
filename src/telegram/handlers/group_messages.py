# coding: utf-8

from typing import cast

from aiogram import F, Router
from aiogram.types import Message, User
from loguru import logger

from api import TelehooperAPI, TelehooperGroup, TelehooperSubGroup


router = Router()
router.message.filter(F.chat.type.in_(["group", "supergroup"]))

async def get_subgroup(msg: Message) -> dict | None:
	"""
	Фильтр для входящих сообщений в группе. Если данная группа является диалог-группой, то данный метод вернёт объект TelehooperSubGroup.
	"""

	# Понятия не имею как, но бот получал свои же сообщения в данном хэндлере.
	if msg.from_user and msg.from_user.is_bot:
		return None

	telehooper_user = await TelehooperAPI.get_user(cast(User, msg.from_user))
	telehooper_group = await TelehooperAPI.get_group(telehooper_user, msg.chat)

	if not telehooper_group:
		return None

	telehooper_group = cast(TelehooperGroup, telehooper_group)

	subgroup = TelehooperAPI.get_subgroup_by_chat(
		telehooper_group,
		msg.message_thread_id or 0
	)

	if not subgroup:
		return None

	return {"subgroup": subgroup}

@router.message(get_subgroup)
async def on_group_message(msg: Message, subgroup: TelehooperSubGroup) -> None:
	"""
	Handler для случая, если бот получил в группе сообщение, для которого существует диалог в сервисе.
	"""

	await subgroup.service.handle_inner_message(msg, subgroup)

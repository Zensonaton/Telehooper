# coding: utf-8

import asyncio
from typing import cast

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Audio, Document, Message, PhotoSize, User, Video
from loguru import logger

from api import (TelehooperAPI, TelehooperGroup, TelehooperSubGroup,
                 TelehooperUser)


_priority_ = -1
"""Приоритет загрузки."""

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

	topic_id = msg.message_thread_id or 0

	# Telegram в msg.message_thread_id возвращает ID сообщения, на которое был ответ.
	# Это ломает всего бота, поэтому нам приходится костылить.
	if not msg.is_topic_message:
		topic_id = 0

	subgroup = TelehooperAPI.get_subgroup_by_chat(telehooper_group, topic_id)

	if not subgroup:
		return None

	return {"subgroup": subgroup, "user": telehooper_user}

@router.message(Command("delete", "del", "d"), get_subgroup)
async def delete_command_handler(msg: Message, subgroup: TelehooperSubGroup, user: TelehooperUser) -> None:
	"""
	Handler для команды `/delete`.
	"""

	if not msg.reply_to_message:
		await msg.reply(
			"<b>⚠️ Ошибка удаления сообщения</b>.\n"
			"\n"
			"Для удаления сообщения необходимо <b>ответить</b> на него командой <code>/delete</code>.\n"
			"«Ответ на сообщение» — то, что сделал я с Вашим сообщением. 🙃",
			allow_sending_without_reply=True
		)

		return

	await subgroup.service.handle_message_delete(msg.reply_to_message, subgroup)

	# Удаляем сообщение (команду), если этого позволяет настройка.
	if await user.get_setting(f"Services.{subgroup.service.service_name}.CleanupAfterUse"):
		await asyncio.sleep(1)

		try:
			await msg.delete()
		except:
			pass

@router.message(Command("read", "r", "mark", "mark_as_read"), get_subgroup)
async def read_command_handler(msg: Message, subgroup: TelehooperSubGroup, user: TelehooperUser) -> None:
	"""
	Handler для команды `/read`.
	"""

	await subgroup.service.handle_message_read(subgroup)

	# Удаляем сообщение (команду), если этого позволяет настройка.
	if await user.get_setting(f"Services.{subgroup.service.service_name}.CleanupAfterUse"):
		await asyncio.sleep(1)

		try:
			await msg.delete()
		except:
			pass

@router.edited_message(get_subgroup)
async def on_message_edit(msg: Message, subgroup: TelehooperSubGroup) -> None:
	"""
	Handler для случая, если пользователь отредактировал сообщение в группе-диалоге (или топик-диалоге).
	"""

	await subgroup.service.handle_message_edit(msg, subgroup)

@router.message(get_subgroup)
async def on_group_message(msg: Message, subgroup: TelehooperSubGroup) -> None:
	"""
	Handler для случая, если бот получил в группе сообщение, для которого существует диалог в сервисе.
	"""

	await subgroup.service.handle_inner_message(msg, subgroup, [])

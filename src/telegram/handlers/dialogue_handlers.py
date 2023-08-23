# coding: utf-8

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from api import (TelehooperSubGroup, TelehooperUser, get_mediagroup,
                 get_subgroup)


_priority_ = -1
"""Приоритет загрузки."""

router = Router()
router.message.filter(F.chat.type.in_(["group", "supergroup"]))

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

	await subgroup.service.handle_telegram_message_delete(msg.reply_to_message, subgroup)

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

	await subgroup.service.handle_telegram_message_read(subgroup)

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

	await subgroup.service.handle_telegram_message_edit(msg, subgroup)

@router.message(get_mediagroup, get_subgroup)
async def on_group_message(msg: Message, subgroup: TelehooperSubGroup, mediagroup: list) -> None:
	"""
	Handler для случая, если бот получил в группе сообщение, для которого существует диалог в сервисе.
	"""

	await subgroup.service.handle_telegram_message(msg, subgroup, mediagroup)

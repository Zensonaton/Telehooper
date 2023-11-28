# coding: utf-8

import asyncio

from aiogram import F, Router
from aiogram.filters import Command, Text
from aiogram.types import CallbackQuery, Message
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

	await subgroup.handle_telegram_message_delete(msg.reply_to_message, user)

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

	await subgroup.handle_telegram_message_read(user)

	# Удаляем сообщение (команду), если этого позволяет настройка.
	if await user.get_setting(f"Services.{subgroup.service.service_name}.CleanupAfterUse"):
		await asyncio.sleep(1)

		try:
			await msg.delete()
		except:
			pass

@router.edited_message(get_subgroup)
async def on_message_edit(msg: Message, subgroup: TelehooperSubGroup, user: TelehooperUser) -> None:
	"""
	Handler для случая, если пользователь отредактировал сообщение в группе-диалоге (или топик-диалоге).
	"""

	await subgroup.handle_telegram_message_edit(msg, user)

@router.message(get_mediagroup, get_subgroup)
async def on_group_message(msg: Message, subgroup: TelehooperSubGroup, user: TelehooperUser, mediagroup: list) -> None:
	"""
	Handler для случая, если бот получил в группе сообщение, для которого существует диалог в сервисе.
	"""

	await subgroup.handle_telegram_message(msg, user, mediagroup)

@router.callback_query(Text(startswith="service-clbck:"), get_subgroup)
async def service_inline_callback_handler(query: CallbackQuery, subgroup: TelehooperSubGroup, user: TelehooperUser) -> None:
	"""
	Inline Callback Handler для случая, если пользователь нажал на Inline Callback кнопку из сервиса.
	"""

	await subgroup.handle_telegram_callback_button(query, user)

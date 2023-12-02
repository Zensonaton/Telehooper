# coding: utf-8

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import api
import utils
from telegram.bot import get_minibots


router = Router()

@router.message(Command("status", "state"))
async def status_command_handler(msg: Message) -> None:
	"""
	Handler для команды `/status`.
	"""

	commit_hash_url = await utils.get_commit_hash()
	if commit_hash_url:
		commit_hash_url = f"<a href=\"https://github.com/Zensonaton/Telehooper/commit/{commit_hash_url}\">{commit_hash_url}</a>"

	await msg.answer(
		"<b>📊 Состояние бота</b>.\n"
		"\n"
		"Техническая информация о боте:\n"
		f" • <b>Commit hash</b>: {commit_hash_url or '<i>⚠️ commit hash неизвестен*</i>'}.\n"
		f" • <b>Версия объектов БД</b>: v{utils.get_bot_version()}.\n"
		f" • <b>RAM usage</b>: {round(utils.get_ram_usage())} МБ.\n"
		f" • <b>Миниботов подключено</b>: {len(get_minibots())} шт.\n"
		f" • <b>Объектов ServiceAPI</b>: {len(api._saved_connections)} шт.\n"
		f" • <b>Объектов TelehooperSubGroup</b>: {len(api._service_dialogues)} шт.\n"
		f" • <b>Кэшированные MIDs</b>: {len(api._cached_message_ids)} шт.\n"
		f" • <b>Кэшированные вложения</b>: {len(api._cached_attachments)} шт.\n"
		"\n"
		f"{'⚠️ Боту не удалось получить commit hash. Это значит, что человек, запустивший этого бота на своём сервере не использовал git. Это плохо, поскольку это может обозначать то, что бот может быть неактуальной либо поддельной версии.' if not commit_hash_url else ''}"
	)

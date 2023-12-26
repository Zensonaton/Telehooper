# coding: utf-8

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import api
import utils
from consts import GITHUB_SOURCES_URL
from telegram.bot import get_minibots


async def get_bot_status_fields() -> str:
	"""
	Возвращает строку, в которой описаны технические поля состояния бота. Такая строка описана в команде `/status`.
	"""

	commit_hash_url = await utils.get_commit_hash()
	if commit_hash_url:
		commit_hash_url = f"<a href=\"{GITHUB_SOURCES_URL}/commit/{commit_hash_url}\">{commit_hash_url}</a>"

	mids_sum = 0
	for mid_objects in api._cached_message_ids.values():
		mids_sum += len(mid_objects)

	return (
		f" • <b>Uptime</b>: {utils.seconds_to_userfriendly_string(utils.time_since(api._start_timestamp))}.\n"
		f" • <b>Commit hash</b>: {commit_hash_url or '<i>⚠️ commit hash неизвестен*</i>'}.\n"
		f" • <b>Версия объектов БД</b>: v{utils.get_bot_version()}.\n"
		f" • <b>RAM usage</b>: {round(utils.get_ram_usage())} МБ.\n"
		f" • <b>Миниботов подключено</b>: {len(get_minibots())} шт.\n"
		f" • <b>Объектов ServiceAPI</b>: {len(api._saved_connections)} шт.\n"
		f" • <b>Объектов TelehooperSubGroup</b>: {len(api._service_dialogues)} шт.\n"
		f" • <b>Кэшированные MIDs</b>: {mids_sum} шт., (при {len(api._cached_message_ids)} объектах)\n"
		f" • <b>Кэшированные вложения</b>: {len(api._cached_attachments)} шт."
	)

router = Router()

@router.message(Command("status", "state"))
async def status_command_handler(msg: Message) -> None:
	"""
	Handler для команды `/status`.
	"""

	has_commit_hash = bool(await utils.get_commit_hash())

	await msg.answer(
		"<b>📊 Состояние бота</b>.\n"
		"\n"
		"Техническая информация о боте:\n"
		f"{await get_bot_status_fields()}\n"
		"\n"
		f"{'⚠️ Боту не удалось получить commit hash. Это значит, что человек, запустивший этого бота на своём сервере не использовал git. Это плохо, поскольку это может обозначать то, что бот может быть неактуальной либо поддельной версии.' if not has_commit_hash else ''}"
	)

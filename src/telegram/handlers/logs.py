# coding: utf-8

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

import utils
from api import TelehooperAPI

router = Router()

@router.message(Command("logs"))
async def logs_command_handler(msg: Message) -> None:
	"""
	Handler для команды `/logs`.
	"""

	assert msg.from_user

	user = await TelehooperAPI.get_user(msg.from_user)

	if not user.has_role("logs"):
		await msg.answer("Нет доступа.")

		return

	await msg.answer_document(
		document=FSInputFile(
			"logs/bot.log",
			filename=f"Telehooper Logs {utils.get_timestamp()}.log"
		),
		caption=(
			"<b>ℹ️ Логи бота</b>.\n"
			"\n"
			"Логи бота."
		)
	)

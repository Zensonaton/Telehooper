# coding: utf-8

import asyncio
import json

from aiogram import Router
from aiogram.types import BufferedInputFile, Message

import utils
from api import CommandWithDeepLink, TelehooperAPI, TelehooperUser
from DB import get_group


router = Router()

async def get_user_data(user: TelehooperUser) -> bytes:
	"""
	Создаёт `.json`-файл с экспортом данных о пользователе.

	:param user: Объект пользователя Telehooper, о котором должна быть извлечена информация.
	"""

	# Извлекаем данные пользователя.
	output_dict = {
		f"user_{user.telegramUser.id}": user.document.json
	}

	# Извлекаем данные о всех группах, с которым связан пользователь.
	for group_id in user.document["Groups"]:
		group = await get_group(group_id)

		assert group, f"Группа {group_id} имеет запись в БД у пользователя, однако сама группа не существует"

		output_dict[f"group_{group_id}"] = group.json

	return (
		f"// Экспорт данных для пользователя бота Telehooper user_{user.telegramUser.id}.\n"
		f"// Запрос на экспорт был произведён в {utils.get_timestamp()} (UNIX timestamp).\n"
		"//"
		"// Пожалуйста, ни с кем не делитесь данным файлом, поскольку в ином случае Вы рискуете своими личными данными!\n"
		"\n"
		f"{json.dumps(output_dict, indent=4, ensure_ascii=False)}"
	).encode("utf-8")

@router.message(CommandWithDeepLink("export_data", "dump_my_data"))
async def export_data_command_handler(msg: Message) -> None:
	"""
	Handler для команды `/export_data`.
	"""

	if not msg.from_user:
		return

	if msg.chat.type != "private":
		await msg.reply(
			"<b>⚠️ Ошибка выполнения команды</b>.\n"
			"\n"
			"Данная команда может быть вызвана только в личных сообщениях с ботом.",
			allow_sending_without_reply=True
		)

		return

	user = await TelehooperAPI.get_user(msg.from_user)

	answer = await msg.answer_document(
		document=BufferedInputFile(
			file=await get_user_data(user),
			filename=f"Экспорт данных Telehooper для user_{msg.from_user.id}.json"
		),
		caption=(
			"<b>🗂  Экспорт данных</b>.\n"
			"\n"
			"Ваши данные были успешно экспортированы в следующий <code>.json</code>-файл. Распрягайтесь своими данными как Вам угодно.\n"
			"Для открытия данного файла рекомендуется воспользоваться редактором <code>.json</code>-файлов либо любым IDE.\n"
			"\n"
			"<b><u>⚠️ НИКОМУ не отправляйте данное сообщение или файл! ⚠️</u></b>\n"
			"Отправив этот файл третьим лицам, Вы подставите сохранность своих же данных под риск. Для Вашей же безопасности, данное сообщение будет удалено через небольшой промежуток времени."
		),
		protect_content=True
	)

	await asyncio.sleep(60)
	try:
		await answer.delete()
	except:
		pass

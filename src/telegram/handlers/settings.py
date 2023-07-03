# coding: utf-8

from typing import cast
from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject, Text

from api import settings
from consts import CommandButtons


router = Router()

async def settings_command_message(msg: types.Message, edit_message: bool = False, path: str | None = None) -> None:
	"""
	Сообщение для команды `/settings`.
	"""

	setting = None
	setting_selected = False

	try:
		setting = settings.get_setting(path or "")
	except:
		pass
	else:
		setting_selected = setting["IsValue"]

	tree_rendered = settings.render_tree(path)

	_text = (
		"<b>⚙️ Настройки</b>.\n"
		"\n"
		"Нажимайте на кнопки ниже что бы перемещаться по разным разделам настроек.\n"
		"\n"
		f"📂 <b>Настройки</b>:\n"
		f"{tree_rendered}"
	)

	if setting_selected:
		setting = cast(dict, setting)
		is_enabled = setting["Default"]

		_text = (
			f"<b>⚙️ Изменение настройки \"{setting['Name']}\"</b>.\n"
			"\n"
			f"📂 <b>Настройки</b>:\n"
			f"{tree_rendered}"
			"\n"
			f"<b>⚙️ {setting['Name']}</b>:\n"
			f"{setting['Documentation']}\n"
			"\n"
			f"<b>⚙️ Текущее значение у настройки</b>:\n"
			f"  • Состояние: {'✔️ включено' if is_enabled else '✖️ выключено'}."
		)

	if edit_message:
		await msg.edit_text(
			_text,
			reply_markup=settings.get_keyboard(path)
		)
	else:
		await msg.answer(
			_text,
			reply_markup=settings.get_keyboard(path)
		)

@router.message(Command("settings", "s", "setting"))
@router.message(Text(CommandButtons.SETTINGS))
async def settings_command_handler(msg: types.Message, command: CommandObject | None = None) -> None:
	"""
	Handler для команды `/settings`.
	"""

	path = ""
	if command and command.args:
		args = command.args.split()

		path = args[0]

	await settings_command_message(msg, path=path)

@router.callback_query(Text(startswith="/settings"), F.message.as_("msg"))
async def settings_select_inline_handler(query: types.CallbackQuery, msg: types.Message):
	"""
	Inline Callback Handler для команды `/help`.

	Вызывается при выборе настройки/папки.
	"""

	path = ""
	path_splitted = (query.data or "").split()
	if len(path_splitted) >= 2:
		path = path_splitted[1]

	await settings_command_message(msg, edit_message=True, path=path)

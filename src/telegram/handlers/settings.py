# coding: utf-8

from typing import cast

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, Text
from aiogram.types import CallbackQuery, Message, User

from api import TelehooperAPI, TelehooperUser, settings
from consts import CommandButtons
from exceptions import SettingNotFoundException


router = Router()

async def settings_command_message(msg: Message, user: TelehooperUser, edit_message: bool = False, path: str | None = None) -> None:
	"""
	Сообщение для команды `/settings`.
	"""

	if not path:
		path = ""

	setting = None
	setting_selected = False

	try:
		setting = settings.get_setting(path)
	except:
		pass
	else:
		setting_selected = setting["IsValue"]

	settings_rendered = settings.get_keyboard(path, user.settingsOverriden)
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
		value = await user.get_setting(path)

		value_str = str(value)
		if isinstance(value, bool):
			value_str = "✔️ Включено" if value else "✖️ Выключено"

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
			f"  • {'Состояние' if type(value) is bool else 'Значение'}: {value_str}."
		)

	await TelehooperAPI.send_or_edit_message(
		text=_text,
		chat_id=msg.chat.id,
		message_to_edit=msg if edit_message else None,
		reply_markup=settings_rendered
	)

@router.message(Command("settings", "s", "setting"))
@router.message(Text(CommandButtons.SETTINGS))
async def settings_command_handler(msg: Message, command: CommandObject | None = None) -> None:
	"""
	Handler для команды `/settings`.
	"""

	assert msg.from_user

	user = await TelehooperAPI.get_user(msg.from_user)

	path = ""
	if command and command.args:
		args = command.args.split()

		path = args[0]

	await settings_command_message(msg, user, path=path)

@router.callback_query(Text(startswith="/settings set"), F.message.as_("msg"), F.from_user.as_("user"))
async def settings_set_inline_handler(query: CallbackQuery, msg: Message, user: User):
	"""
	Inline Callback Handler для команды `/help`.

	Вызывается при изменении значения настройки.
	"""

	assert msg.from_user

	telehooper_user = await TelehooperAPI.get_user(user)

	path_splitted = (query.data or "").split()
	if len(path_splitted) < 3:
		return

	path = path_splitted[2]
	value = path_splitted[3]

	value_parsed = value
	if value.isdigit():
		value_parsed = int(value)
	elif value in ["True", "False"]:
		value_parsed = value == "True"
	else:
		raise ValueError(f"Задано значение \"{value}\" для настройки \"{path}\", которое не может быть преобразовано.")

	try:
		setting = settings.get_setting(path)

		if not setting["IsValue"]:
			raise SettingNotFoundException(f"Настройка \"{path}\" не является настройкой, а папкой.")
	except:
		raise SettingNotFoundException(f"Настройка \"{path}\" не найдена.")

	await telehooper_user.save_setting(path, value_parsed)
	await settings_command_message(msg, telehooper_user, edit_message=True, path=path)

@router.callback_query(Text(startswith="/settings"), F.message.as_("msg"), F.from_user.as_("user"))
async def settings_select_inline_handler(query: CallbackQuery, msg: Message, user: User):
	"""
	Inline Callback Handler для команды `/help`.

	Вызывается при выборе настройки/папки.
	"""

	assert msg.from_user

	telehooper_user = await TelehooperAPI.get_user(user)

	path = ""
	path_splitted = (query.data or "").split()
	if len(path_splitted) >= 2:
		path = path_splitted[1]

	if path:
		try:
			settings.get_setting(path)
		except:
			raise SettingNotFoundException(f"Настройка \"{path}\" не найдена.")

	await settings_command_message(msg, telehooper_user, edit_message=True, path=path)

# coding: utf-8

from typing import cast

from aiogram import F, Bot, Router
from aiogram.filters import CommandObject
from aiogram.types import CallbackQuery, Message, User

import utils
from api import CommandWithDeepLink, TelehooperAPI, TelehooperUser, settings
from config import config
from consts import CommandButtons
from exceptions import SettingNotFoundException


router = Router()

async def settings_command_message(msg: Message, bot: Bot, user: TelehooperUser, edit_message: bool = False, path: str | None = None) -> None:
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

	tree_rendered = settings.render_tree(path, user.settingsOverriden)
	settings_keyboard = settings.get_keyboard(path, user.settingsOverriden)

	debug_setting_paths = ""
	if config.debug and await user.get_setting("Debug.ShowSettingPaths"):
		debug_setting_paths = utils.replace_placeholders(
			"\n"
			"{{Debug.ShowSettingPaths}}: <code>" + path + "</code>.\n"
		)

	_text = (
		"<b>⚙️ Настройки</b>.\n"
		f"{debug_setting_paths}"
		"\n"
		"Нажимайте на кнопки ниже что бы перемещаться по разным разделам настроек.\n"
		"\n"
		f"📂 <b>Настройки</b>:\n"
		f"{tree_rendered}"
	)

	if setting_selected:
		setting = cast(dict, setting)
		value = await user.get_setting(path)

		current_value = "  • "
		if setting["ButtonType"] == "bool":
			current_value += f"Состояние: {'✔️ Включено' if value else '✖️ Выключено'}"
		elif setting["ButtonType"] == "range":
			current_value += f"Значение: {value}"
		elif setting["ButtonType"] == "enum":
			current_value += f"Значение: {setting['EnumValues'][str(value)]}"

		_text = (
			f"<b>⚙️ Изменение настройки \"{setting['Name']}\"</b>.\n"
			f"{debug_setting_paths}"
			"\n"
			f"📂 <b>Настройки</b>:\n"
			f"{tree_rendered}"
			"\n"
			f"<b>⚙️ {setting['Name']}</b>:\n"
			f"{utils.replace_placeholders(setting['Documentation'])}\n"
			"\n"
			f"<b>⚙️ Текущее значение у настройки</b>:\n"
			f"{current_value}."
		)

	await TelehooperAPI.edit_or_resend_message(
		bot,
		text=_text,
		chat_id=msg.chat.id,
		message_to_edit=msg if edit_message else None,
		reply_markup=settings_keyboard,
		disable_web_page_preview=True
	)

@router.message(CommandWithDeepLink("settings", "s", "setting"))
@router.message(F.text == CommandButtons.SETTINGS)
async def settings_command_handler(msg: Message, bot: Bot, command: CommandObject | None = None) -> None:
	"""
	Handler для команды `/settings`.
	"""

	assert msg.from_user

	user = await TelehooperAPI.get_user(msg.from_user)

	path = ""
	if command and command.args:
		args = command.args.split()

		path = args[0]

	await settings_command_message(msg, bot, user, path=path)

@router.callback_query(F.data.startswith("/settings set"), F.message.as_("msg"), F.from_user.as_("user"))
async def settings_set_inline_handler(query: CallbackQuery, msg: Message, user: User, bot: Bot):
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
		pass

	try:
		setting = settings.get_setting(path)

		if not setting["IsValue"]:
			raise SettingNotFoundException(f"Настройка \"{path}\" не является настройкой, а папкой.")
	except:
		raise SettingNotFoundException(f"Настройка \"{path}\" не найдена.")

	await telehooper_user.save_setting(path, value_parsed)
	await settings_command_message(msg, bot, telehooper_user, edit_message=True, path=path)

@router.callback_query(F.data.startswith("/settings"), F.message.as_("msg"), F.from_user.as_("user"))
async def settings_select_inline_handler(query: CallbackQuery, msg: Message, user: User, bot: Bot):
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

	await settings_command_message(msg, bot, telehooper_user, edit_message=True, path=path)

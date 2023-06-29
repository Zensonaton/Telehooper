# coding: utf-8

from aiogram import F
from aiogram import Router
from aiogram import types
from aiogram.filters import Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


router = Router()

def _groupConnectKeyboard(show_more_info_button: bool = True) -> InlineKeyboardMarkup:
	"""
	Генерирует клавиатуру для команды /this.
	"""

	top_row = [InlineKeyboardButton(text="🔙 Назад", callback_data="/this")]

	if show_more_info_button:
		top_row.append(InlineKeyboardButton(text="👋 Мне нужна помощь", callback_data="/this vk showMoreInfo"))

	return InlineKeyboardMarkup(inline_keyboard=[
		top_row,

		[InlineKeyboardButton(text="🗨 Топики-диалоги", callback_data="do-nothing")], # TODO: Настоящие callback_data.
		[InlineKeyboardButton(text="👤 Группа-диалог", callback_data="do-nothing")],

		[InlineKeyboardButton(text="🗞 Группа с лентой новостей", callback_data="do-nothing")],
		[InlineKeyboardButton(text="🫂 Группа-сообщество", callback_data="do-nothing")],
	])

@router.callback_query(Text("/this vk connect"), F.message.as_("message"))
async def this_vk_inline_handler(query: types.CallbackQuery, message: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем кнопку "ВКонтакте" в команде `/this`.
	"""

	await message.edit_text(
		"<b>🫂 Группа-диалог — ВКонтакте</b>.\n"
		"\n"
		"В данный момент, Вы пытаетесь соединить данную группу Telegram с сообществом либо же диалогом ВКонтакте.\n"
		"Сделайте выбор, какой именно тип группы-диалога Вы хотите создать.\n"
		"\n"
		"ℹ️ Не понимаете что нужно выбрать? В таком случае нажмите на кнопку «Мне нужна помощь», либо воспользуйтесь командой <code>/faq 5</code>.",
		disable_web_page_preview=True,
		reply_markup=_groupConnectKeyboard(True)
	)

@router.callback_query(Text("/this vk showMoreInfo"), F.message.as_("message"))
async def this_show_more_info_inline_handler(query: types.CallbackQuery, message: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается, когда пользователь нажал на кнопку "Мне нужна помощь" в команде `/this`.
	"""

	await message.edit_text(
		"<b>🫂 Группа-диалог — ВКонтакте</b>.\n"
		"\n"
		"В данный момент, Вы пытаетесь соединить данную группу Telegram с сообществом либо же диалогом ВКонтакте.\n"
		"Сделайте выбор, какой именно тип группы-диалога Вы хотите создать.\n"
		"\n"
		"<b><u>✉️ Работа с сообщениями</u></b>:\n"
		"Вы хотите получить доступ <b>сразу ко всем</b> диалогам ВКонтакте?\n"
		"  — Используйте <b>«Топик-диалог»</b>.\n"
		"Рекомендуется использовать данный вариант, если Вы пользуетесь ботом впервые, поскольку все новые чаты будут появляться именно в этой группе.\n"
		"\n"
		"Вы хотите получить доступ лишь <b>к единственному</b> диалогу с сервиса?\n"
		"  — Используйте <b>«Группу-диалог»</b>.\n"
		"Используйте данный вариант при общении с «важными» персонами, поскольку в таком случае Вы будете реже встречать лимиты Telegram, а так же пользоваться таким диалогом будет проще нежели топиками.\n"
		"\n"
		"<b><u>🫂 Работа с сообществами</u></b>:\n"
		"Вы хотите получить <b>все новости</b> из сообществ ВКонтакте?\n"
		"  — Используйте <b>«Группу с лентой новостей»</b>.\n"
		"\n"
		"Вы хотите получать посты лишь с <b>одного конкретного</b> сообщества?\n"
		"  — Используйте <b>«Группу-сообщество»</b>.\n"
		"Удобно, если Вы хотите классифицировать отдельные сообщества по отдельным группам Telegram.\n"
		"\n"
		"ℹ️ Всё равно не понимаете о чём идет речь? В таком случае воспользуйтесь командой <code>/faq 5</code>.",
		disable_web_page_preview=True,
		reply_markup=_groupConnectKeyboard(False)
	)

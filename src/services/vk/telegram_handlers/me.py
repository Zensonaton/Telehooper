# coding: utf-8

from aiogram import F, Router, types
from aiogram.filters import Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api import TelehooperAPI
from services.service_api_base import ServiceDisconnectReason


router = Router()

@router.callback_query(Text("/me vk"), F.message.as_("msg"))
async def me_vk_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Открывает меню с управлением сервиса ВКонтакте.
	Вызывается при нажатии пользователем кнопки "ВКонтакте" в команде `/me`.
	"""

	assert msg.from_user

	user = await TelehooperAPI.get_user(query.from_user)

	keyboard = InlineKeyboardMarkup(
		inline_keyboard=[
			[
				InlineKeyboardButton(text="🔙 Назад", callback_data="/me"),
			],

			[
				InlineKeyboardButton(text="🔑 Добавить токен", callback_data="/me vk multitokens"),
				InlineKeyboardButton(text="⛔️ Отключить от бота", callback_data="/me vk disconnect"),
			]
		]
	)

	id = user.connections["VK"]["ID"]
	full_name = user.connections["VK"]["FullName"]
	domain = user.connections["VK"]["Username"]

	await msg.edit_text(
		"<b>👤 Ваш профиль — ВКонтакте</b>.\n"
		"\n"
		"Вы управляете этой ВКонтакте через бота:\n"
		f" • <b>Страница</b>: {full_name} (<a href=\"vk.com/{domain}\">@{domain}</a>, ID {id}).\n"
		"\n"
		"Диалогов и групп ВКонтакте в боте — 3 штук(-и):\n" # TODO: Использовать реальные данные.
		" • <b>Имя Фамилия</b>: <a href=\"vk.com/id1\">Группа</a>.\n"
		" • <b>Имя Фамилия</b>: <a href=\"vk.com/id1\">Группа</a>.\n"
		" • <b>ВКонтакте API</b>: <a href=\"vk.com/club1\">Канал</a>.\n",
		reply_markup=keyboard,
		disable_web_page_preview=True
	)

@router.callback_query(Text("/me vk multitokens"), F.message.as_("msg"))
async def me_vk_multitokens_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Вызывается при нажатии на кнопку "Добавить токен" в меню управления ВКонтакте.
	"""

	keyboard = InlineKeyboardMarkup(
		inline_keyboard=[
			[
				InlineKeyboardButton(text="🔙 Назад", callback_data="/me vk"),
				InlineKeyboardButton(text="🔝 В начало", callback_data="/me"),
			],
		]
	)

	await msg.edit_text(
		"Данная опция ещё находится в разработке.",
		reply_markup=keyboard,
		disable_web_page_preview=True
	)

@router.callback_query(Text("/me vk disconnect"), F.message.as_("msg"))
async def me_vk_disconnect_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Вызывается при нажатии на кнопку "Отключить от бота" в меню управления ВКонтакте.
	"""

	user = await TelehooperAPI.get_user(query.from_user)

	keyboard = InlineKeyboardMarkup(
		inline_keyboard=[
			[
				InlineKeyboardButton(text="🔙 Назад", callback_data="/me vk"),
				InlineKeyboardButton(text="🔝 В начало", callback_data="/me"),
			],

			[
				InlineKeyboardButton(text="⛔️ Да, отключить", callback_data="/me vk disconnect confirm"),
			]
		]
	)

	await msg.edit_text(
		"<b>⛔️ Отключение ВКонтакте</b>.\n"
		"\n"
		f"Вы уверены, что хотите отключить страницу «{user.connections['VK']['FullName']}» от Telehooper?\n"
		"\n"
		"⚠️ Отключив страницу, Telehooper перестанет получать сообщения от ВКонтакте.\n",
		reply_markup=keyboard
	)

@router.callback_query(Text("/me vk disconnect confirm"), F.message.as_("msg"))
async def me_vk_disconnect_confirm_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Вызывается при нажатии на кнопку "Да, отключить" в меню управления ВКонтакте.
	"""

	user = await TelehooperAPI.get_user(query.from_user)
	vkService = user.get_vk_connection()

	assert vkService

	await vkService.disconnect_service(ServiceDisconnectReason.INITIATED_BY_USER)

	keyboard = InlineKeyboardMarkup(
		inline_keyboard=[
			[
				InlineKeyboardButton(text="🔝 В начало", callback_data="/me"),
			],
		]
	)

	await msg.edit_text(
		"<b>⛔️ Отключение ВКонтакте</b>.\n"
		"\n"
		f"Страница «{user.connections['VK']['FullName']}» была отключена от Telehooper.\n"
		"\n"
		"ℹ️ Вы можете снова подключиться, введя команду /connect.\n",
		reply_markup=keyboard
	)

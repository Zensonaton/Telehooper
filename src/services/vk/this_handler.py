# coding: utf-8

from aiogram import F
from aiogram import Router
from aiogram import types
from aiogram.filters import Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


router = Router()

@router.callback_query(Text("/this vk"), F.message.as_("msg"))
async def this_vk_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем кнопки "ВКонтакте" в команде `/this`.
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="🔙 Назад", callback_data="/this")],

		[InlineKeyboardButton(text="💬 Сообщения и общаться", callback_data="/this vk messages")],
		[InlineKeyboardButton(text="🗞 Новости/посты из групп", callback_data="/this vk posts")],
	])

	await msg.edit_text(
		"<b>🫂 Группа-диалог — ВКонтакте</b>.\n"
		"\n"
		"В данный момент, Вы пытаетесь соединить данную группу Telegram с сообществом либо же диалогом ВКонтакте.\n"
		"Ответив на вопросы бот определит, какую роль будет выполнять данная группа.\n"
		"\n"
		"<b>❓ Что Вы хотите получать из ВКонтакте</b>?",
		reply_markup=keyboard
	)

@router.callback_query(Text("/this vk messages"), F.message.as_("msg"))
async def this_vk_messages_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем кнопку "Хочу получать сообщения и общаться" в команде `/this`.
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="🔙 Назад", callback_data="/this vk")],

		[InlineKeyboardButton(text="👥 Telegram-группа для всех чатов ВК", callback_data="do-nothing")],
		[InlineKeyboardButton(text="👤 Один чат ВК - одна Telegram-группа", callback_data="do-nothing")],
	])

	await msg.edit_text(
		"<b>🫂 Группа-диалог — ВКонтакте — сообщения</b>.\n"
		"\n"
		"Вы пытаетесь получать <b>сообщения</b> из ВКонтакте. Если Вы ошиблись с выбором, то нажмите на кнопку «назад».\n"
		"Следующий вопрос:\n"
		"\n"
		"<b>❓ Как Вам будет удобно получать сообщения</b>?\n"
		"\n"
		"ℹ️ Вы не создали «общую» группу в Telegram, рекомендуется выбрать «Telegram-группа для всех чатов». Без такой группы Telehooper не сможет отправлять сообщения от новых людей.", # TODO: Проверка на это.
		reply_markup=keyboard
	)

@router.callback_query(Text("/this vk posts"), F.message.as_("msg"))
async def this_vk_posts_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем кнопку "Хочу читать новости/посты из групп" в команде `/this`.
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="🔙 Назад", callback_data="/this vk")],

		[InlineKeyboardButton(text="🗞 Все новости в одной Telegram-группе", callback_data="do-nothing")],
		[InlineKeyboardButton(text="🫂 Одно сообщество ВК - одна Telegram-группа", callback_data="do-nothing")],
	])

	await msg.edit_text(
		"<b>🫂 Группа-диалог — ВКонтакте — посты/новости</b>.\n"
		"\n"
		"Вы пытаетесь получать <b>посты или новости</b> из ВКонтакте. Если Вы ошиблись с выбором, то нажмите на кнопку «назад».\n"
		"Следующий вопрос:\n"
		"\n"
		"<b>❓ Как именно Вы хотите получать посты или новости</b>?",
		reply_markup=keyboard
	)

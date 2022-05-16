# coding: utf-8

"""Обработчик для команды `ThisDialogue`."""

import logging
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from aiogram.types import Message as MessageType
from Consts import InlineButtonCallbacks as CButton
from Exceptions import CommandAllowedOnlyInBotDialogue
from MiddlewareAPI import MiddlewareAPI

if TYPE_CHECKING:
	from TelegramBot import Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper):
	"""
	Инициализирует команду `ThisDialogue`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(ThisDialogue, commands=["thisdialogue", "dialogue"])
	DP.register_callback_query_handler(ThisDialogueCallbackHandler, lambda query: query.data in [CButton.DIALOGUE_SELECTOR_MENU_VK])
	DP.register_callback_query_handler(VKDialogueSelector, lambda query: query.data.startswith(CButton.DIALOGUE_SELECT_VK))


async def ThisDialogue(msg: MessageType):
	if msg.chat.type == "private": # TODO: Нормальную проверку.
		raise CommandAllowedOnlyInBotDialogue()

	await SendThisDialogueMessage(msg)

async def SendThisDialogueMessage(msg: MessageType, edit_message_instead: bool = False):
	_text = "ℹ️ Эта группа не подключена ни к какому из диалогов сервиса.\n\n⚙️ Пожалуйста, выбери из подключённых сервисов:"

	# TODO: Кнопка "Зарезервирать эту группу".

	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton(text="ВКонтакте", callback_data=CButton.DIALOGUE_SELECTOR_MENU_VK)
	)

	if edit_message_instead:
		await msg.edit_text(_text, reply_markup=keyboard)
		return

	await msg.answer(_text, reply_markup=keyboard)

async def ThisDialogueCallbackHandler(query: CallbackQuery):
	if query.data == CButton.DIALOGUE_SELECTOR_MENU_VK:
		_text = "<b>Отлично!</b> Теперь ты можешь выбрать нужный тебе диалог сервиса."

		await query.message.edit_text(f"{_text}\n\n⏳ Позволь мне загрузить все чаты из твоего аккаунта ВК...")

		# Восстанавливаем сессию ВК:
		mAPI = MiddlewareAPI(query.from_user)
		await mAPI.restoreFromDB()

		# Получаем список всех диалогов:
		user_convos = await mAPI.vkAccount.getDialoguesList()

		prefixEmojiDict = {
			"group": "🫂",
			"user_True": "🙋‍♂️", # Эмодзи мужчины
			"user_False": "🙋‍♀️", # Эмодзи женщины
			"chat": "💬",
		}

		keyboard = InlineKeyboardMarkup()
		for index, convo in enumerate(user_convos):
			if index >= 12:
				# Если что-то пойдет не так, и юзер слишком уж общительный, и
				# имеет больше чем 12 человек в своих диалогах, то
				# просто прекращаем работу цикла, иначе бот ответит миллиардом кнопок.

				break

			if convo.isSelf:
				# Пропускаем диалог с самим собой (Избранное)

				continue


			buttonText = f"{prefixEmojiDict[(convo._type + '_' + str(convo.isMale)) if convo.isUser else convo._type]} {convo.fullName} {'📌' if convo.isPinned else ''}"

			keyboard.add(InlineKeyboardButton(buttonText, callback_data=f"{CButton.DIALOGUE_SELECT_VK}{convo.id}"))

		await query.message.edit_text(f"{_text}\n\n⚙️ Выбери нужный тебе диалог из <b>«ВКонтакте»</b>:", reply_markup=keyboard)

	return await query.answer()

async def VKDialogueSelector(query: CallbackQuery):
	VK_ID = query.data.split(CButton.DIALOGUE_SELECT_VK)[-1]

	return await query.answer(VK_ID)

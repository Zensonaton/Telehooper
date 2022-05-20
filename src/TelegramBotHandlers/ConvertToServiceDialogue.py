# coding: utf-8

"""Обработчик для команды `ConvertToServiceDialogue`."""

import asyncio
import logging
from typing import Tuple

from aiogram import Bot, Dispatcher
import aiogram
from aiogram.types import (CallbackQuery, Chat, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from aiogram.types import Message as MessageType
from aiogram.types import User
from Consts import CommandThrottleNames as CThrottle
from Consts import InlineButtonCallbacks as CButton
from Exceptions import CommandAllowedOnlyInGroup
from TelegramBot import Telehooper

from TelegramBotHandlers.Dialogue import ThisDialogue

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `ConvertToServiceDialogue`.
	"""

	global Bot, TGBot, DP

	Bot = bot
	TGBot = Bot.TGBot
	DP = Bot.DP

	DP.register_message_handler(ConvertToServiceDialogue, commands=["converttodialogue", "converttoservicedialogue"])
	DP.register_callback_query_handler(DialogueConvertCallback, lambda query: query.data == CButton.CONVERT_GROUP_TO_DIALOGUE)
	DP.register_callback_query_handler(DialogueMenuCallback, lambda query: query.data == CButton.BACK_TO_GROUP_CONVERTER)

async def ConvertToServiceDialogue(msg: MessageType) -> None:
	await DP.throttle(CThrottle.DIALOGUE_CONVERT, rate=3, chat_id=msg.chat.id)

	if not msg.chat.type.endswith("group"):
		raise CommandAllowedOnlyInGroup

	await ConvertToDialogueMessage(msg)

async def ConvertToDialogueMessage(msg: MessageType, edit_message_instead: bool = False) -> None:
	CONDITIONS_MET = await CheckServiceDialogueConversionConditions(msg.chat, msg.from_user)
	ALL_CONDITIONS_ARE_MET = all(CONDITIONS_MET)

	_text = f"""<b>⚠️ Предупреждение! Потенциально разрушительная команда! ⚠️</b>

Ты использовал команду, необходимую для конвертирования Telegram-группы в <b>диалог</b>.
Это значит, что под конкретного пользователя/беседу подключённого сервиса можно сделать отдельный диалог в <b>Telegram</b>!

<b>ℹ️ Существуют некоторые лимиты:</b>
 <b>•</b> <b>1</b> диалог подключённого сервиса — <b>1 группа</b>,
 <b>•</b> Лимит Telegram по количеству групп — <b>500 штук</b> (<a href=\"https://limits.tginfo.me/ru-RU\">клик</a>),
 <b>•</b> В день можно создавать <b>50 групп</b> (<a href=\"https://limits.tginfo.me/ru-RU\">клик</a>).

<b>ℹ️ После конвертирования у группы изменится:</b>
 <b>•</b> Название; на имя диалога,
 <b>•</b> Фотография; на фото диалога,
 <b>•</b> Описание.

{"Все следующие условия для преобразования группы были соблюдены" if ALL_CONDITIONS_ARE_MET else "Продолжить можно, если выполнить все следующие <b>условия</b> для преобразования группы"}:
 {"✅" if CONDITIONS_MET[0] else "☑️"} Ты должен быть администратором в группе,
 {"✅" if CONDITIONS_MET[1] else "☑️"} У бота должны права администратора,
 {"✅" if CONDITIONS_MET[2] else "☑️"} Данная группа не должна уже быть диалогом.

{"Если ты согласен, то нажми на кнопку ниже:" if ALL_CONDITIONS_ARE_MET else "<b>Продолжить можно после выполнения всех условий, описанных выше❗️</b>"}
"""

	keyboard = InlineKeyboardMarkup()

	if ALL_CONDITIONS_ARE_MET:
		keyboard.add(
			InlineKeyboardButton("⚙️ Конвертировать", callback_data=CButton.CONVERT_GROUP_TO_DIALOGUE)
		)

	keyboard.insert(
		InlineKeyboardButton("🔙 Отмена", callback_data=CButton.CANCEL_EDIT_CUR_MESSAGE)
	)


	if edit_message_instead:
		await msg.edit_text(_text, reply_markup=keyboard)
		return

	await msg.reply(_text, reply_markup=keyboard)

async def CheckServiceDialogueConversionConditions(chat: Chat, user: User) -> Tuple[bool, bool, bool]:
	"""
	Выдаёт Tuple с Boolean-значениями, обозначающие выполнение всех необходимых условий для преобразования Telegram группы в диалог сервиса.
	"""

	USER_SENDER_IS_ADMIN: bool = False
	BOT_IS_ADMIN: bool = False
	NOT_CONNECTED_AS_DIALOGUE: bool = True # TODO

	# Получаем список админов в чате:
	chat_admins = (await TGBot.get_chat_administrators(chat.id))

	USER_SENDER_IS_ADMIN = bool([i for i in chat_admins if i.user.id == user.id])
	BOT_IS_ADMIN = bool([i for i in chat_admins if i.user.id == TGBot.id])

	return (
		USER_SENDER_IS_ADMIN,
		BOT_IS_ADMIN,
		NOT_CONNECTED_AS_DIALOGUE
	)

async def DialogueConvertCallback(query: CallbackQuery):
	CONDITIONS_MET = await CheckServiceDialogueConversionConditions(query.message.chat, query.message.from_user)
	ALL_CONDITIONS_ARE_MET = all(CONDITIONS_MET)

	if not ALL_CONDITIONS_ARE_MET:
		return await query.answer("Не все условия для преобразования были соблюдены, отправь команду снова.")

	await ConvertGroupToDialogue(query.message.chat)

	await asyncio.sleep(0)

	await query.message.edit_text(query.message.html_text)
	await query.message.answer("<b>Отлично!</b> Данная группа была успешно конвертирована в диалог! ☺️\n\nТеперь тебе необходимо выбрать, к какому диалогу подключённого сервиса эта группа должна быть подсоединена: Именно с выбранного диалога сообщения будут пересылаться сюда, и тут же на них ты будешь отвечать, для этого ты можешь воспользоваться командою /dialogue. Удоства ради, я использую её за тебя:")
	await ThisDialogue(query.message)

	return await query.answer()

async def DialogueMenuCallback(query: CallbackQuery) -> None:
	await ConvertToDialogueMessage(query.message, True)

async def ConvertGroupToDialogue(chat: Chat) -> None:
	"""
	Переводит группу в диалог.
	"""

	# TODO: Предупредить пользователя о изменениях при переводе группы.
	await chat.set_title("ㅤ")

	try:
		await chat.delete_photo()
	except: pass

	try:
		await chat.set_description("[Telehooper] Пустой диалог сервиса.")
	except: pass

# coding: utf-8

"""Handler для команды `ConvertToServiceDialogue`."""

from typing import Tuple
from aiogram.types import Message as MessageType, Chat, User, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from Consts import InlineButtonCallbacks as CButton
from aiogram import Dispatcher, Bot
from Exceptions import CommandAllowedOnlyInGroup
import logging

BOT: Bot = None  # type: ignore
logger = logging.getLogger(__name__)

def _setupCHandler(dp: Dispatcher, bot: Bot):
	"""
	Инициализирует команду `ConvertToServiceDialogue`.
	"""

	global BOT

	BOT = bot
	dp.register_message_handler(ConvertToServiceDialogue, commands=["converttodialogue", "converttoservicedialogue"])
	dp.register_callback_query_handler(DialogueConvertCallback, lambda query: query.data == CButton.CONVERT_GROUP_TO_DIALOGUE)
	dp.register_callback_query_handler(DialogueMenuCallback, lambda query: query.data == CButton.BACK_TO_GROUP_CONVERTER)

async def ConvertToServiceDialogue(msg: MessageType):
	# TODO: dp.throttle

	if not msg.chat.type.endswith("group"):
		raise CommandAllowedOnlyInGroup

	await ConvertToDialogueMessage(msg)

async def ConvertToDialogueMessage(msg: MessageType, edit_message_instead: bool = False):
	CONDITIONS_MET = await CheckServiceDialogueConversionConditions(msg.chat, msg.from_user)
	ALL_CONDITIONS_ARE_MET = all(CONDITIONS_MET)

	_text = f"""<b>⚠️ Предупреждение! Потенциально разрушительная команда! ⚠️</b>

Ты использовал команду, необходимую для конвертирования <b>Telegram-группы</b> в <b>диалог</b>. 
Это значит, что новые сообщения <b>подключённого сервиса</b> будут отправляться <b>в эту группу</b>, и отвечать на них нужно будет именно <b>в этой группе</b>.
Если более простым языком, то под конкретного пользователя можно сделать отдельный <b>диалог</b> в Telegram! 

ℹ️ Однако, существуют некоторые лимиты:
 <b>•</b> <b>1</b> диалог подключённого сервиса — <b>1 группа</b>,
 <b>•</b> Лимит Telegram по количеству групп — <b>500 штук</b> (<a href=\"https://limits.tginfo.me/ru-RU\">клик</a>),
 <b>•</b> В день можно создавать <b>50 групп</b> (<a href=\"https://limits.tginfo.me/ru-RU\">клик</a>).

{"Все следующие условия для преобразования группы <b>были соблюдены</b>" if ALL_CONDITIONS_ARE_MET else "Продолжить можно, если выполнить все следующие <b>условия</b> для <b>преобразования группы</b>"}:
 {"✅" if CONDITIONS_MET[0] else "☑️"} Ты должен быть администратором в группе,
 {"✅" if CONDITIONS_MET[1] else "☑️"} У бота должны все права в беседе, включая права администратора,
 {"✅" if CONDITIONS_MET[2] else "☑️"} Данная группа не должна быть уже подключённым диалогом.

{"Если ты согласен, то нажми на кнопку ниже:" if ALL_CONDITIONS_ARE_MET else "<b>Продолжить можно после выполнения всех условий, описанных выше❗️</b>"}
"""

	keyboard = InlineKeyboardMarkup()
	
	if ALL_CONDITIONS_ARE_MET:
		keyboard.add(
			InlineKeyboardButton("Конвертировать", callback_data=CButton.CONVERT_GROUP_TO_DIALOGUE)
		)

	keyboard.insert(
		InlineKeyboardButton("Отмена", callback_data=CButton.CANCEL_EDIT_CUR_MESSAGE)
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
	chat_admins = (await BOT.get_chat_administrators(chat.id))

	USER_SENDER_IS_ADMIN = bool([i for i in chat_admins if i.user.id == user.id])
	BOT_IS_ADMIN = bool([i for i in chat_admins if i.user.id == BOT.id])

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

	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton("Назад", callback_data=CButton.BACK_TO_GROUP_CONVERTER)
	)

	await ConvertGroupToDialogue(query.message.chat)
	await query.message.edit_text("<b>Отлично!</b> Данная группа была успешно конвертирована в диалог! ☺️\n\nТеперь тебе необходимо выбрать, к какому диалогу подключённого сервиса эта группа должна быть подсоединена: Именно с выбранного диалога сообщения будут пересылаться сюда, и тут же на них ты будешь отвечать.", reply_markup=keyboard)
	# TODO: Отправить команду с настройкой текущего чата.

	return await query.answer()

async def DialogueMenuCallback(query: CallbackQuery):
	await ConvertToDialogueMessage(query.message, True)

async def ConvertGroupToDialogue(chat: Chat):
	"""
	Переводит группу в диалог.
	"""

	# TODO: Предупредить пользователя о изменениях при переводе группы.
	await chat.set_title("ㅤ")

	if chat.photo:
		await chat.delete_photo()

	try:
		await chat.set_description("[Telehooper] Пустой диалог сервиса.")
	except: pass

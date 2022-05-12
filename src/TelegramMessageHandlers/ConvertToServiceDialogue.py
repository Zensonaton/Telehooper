# coding: utf-8

"""Handler для команды `ConvertToServiceDialogue`."""

from typing import Tuple
from aiogram.types import Message as MessageType, Chat, User, InlineKeyboardButton, InlineKeyboardMarkup
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


async def ConvertToServiceDialogue(msg: MessageType):
	# TODO: dp.throttle

	if not msg.chat.type.endswith("group"):
		raise CommandAllowedOnlyInGroup

	CONDITIONS_MET = await checkServiceDialogueConversionConditions(msg.chat, msg.from_user)
	ALL_CONDITIONS_ARE_MET = all(CONDITIONS_MET)


	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton("Конвертировать", callback_data=CButton.CONVERT_GROUP_TO_DIALOGUE),
		InlineKeyboardButton("Отмена", callback_data=CButton.CANCEL_EDIT_CUR_MESSAGE)
	)

	await msg.reply(f"""<b>⚠️ Предупреждение! Потенциально разрушительная команда! ⚠️</b>

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
""", reply_markup=keyboard)

async def checkServiceDialogueConversionConditions(chat: Chat, user: User) -> Tuple[bool, bool, bool]:
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

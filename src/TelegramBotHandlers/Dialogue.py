# coding: utf-8

"""Обработчик для команды `ThisDialogue`."""

import io
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputFile)
from aiogram.types import Message as MessageType
import aiohttp
from Consts import InlineButtonCallbacks as CButton
from Exceptions import CommandAllowedOnlyInBotDialogue
from TelegramBot import DialogueGroup, Telehooper

Bot: 	Telehooper 	= None # type: ignore
TGBot: 	Bot 		= None # type: ignore
DP: 	Dispatcher 	= None # type: ignore

logger = logging.getLogger(__name__)


def _setupCHandler(bot: Telehooper) -> None:
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


async def ThisDialogue(msg: MessageType) -> None:
	if msg.chat.type == "private": # TODO: Нормальную проверку.
		raise CommandAllowedOnlyInBotDialogue()

	await SendThisDialogueMessage(msg)

async def SendThisDialogueMessage(msg: MessageType, edit_message_instead: bool = False) -> None:
	_text = "ℹ️ Эта группа не подключена ни к какому из диалогов сервиса.\n\n⚙️ Пожалуйста, выбери из подключённых сервисов:"

	# TODO: Кнопка "Зарезервирать эту группу".

	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton(text="ВКонтакте", callback_data=CButton.DIALOGUE_SELECTOR_MENU_VK)
	)

	if edit_message_instead:
		await msg.edit_text(_text, reply_markup=keyboard)
		return

	await msg.answer(_text, reply_markup=keyboard)

async def ThisDialogueCallbackHandler(query: CallbackQuery) -> None:
	if query.data == CButton.DIALOGUE_SELECTOR_MENU_VK:
		_text = "<b>Отлично!</b> Теперь ты можешь выбрать нужный тебе диалог сервиса."

		await query.message.edit_text(f"{_text}\n\n⏳ Позволь мне загрузить все чаты из твоего аккаунта ВК...")

		# Получаем объект пользователя:
		user = await Bot.getBotUser(query.from_user.id)

		# Получаем список всех диалогов:
		user_convos = await user.vkAccount.retrieveDialoguesList()

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

			keyboard.add(InlineKeyboardButton(buttonText, callback_data=f"{CButton.DIALOGUE_SELECT_VK}{convo.ID}"))

		await query.message.edit_text(f"{_text}\n\n⚙️ Выбери нужный тебе диалог из <b>«ВКонтакте»</b>:", reply_markup=keyboard)

	return await query.answer()

async def VKDialogueSelector(query: CallbackQuery) -> None:
	VK_ID = int(query.data.split(CButton.DIALOGUE_SELECT_VK)[-1])

	# Получаем информацию:
	user = await Bot.getBotUser(query.from_user.id)

	# Проверяем, не является ли группа диалогом:
	if await user.getDialogueGroupByTelegramGroup(query.message.chat.id):
		return await query.answer("Эта группа уже является диалогом.")

	dialogue = user.vkAccount.getDialogueByID(VK_ID)
	assert dialogue, "dialogue is None"

	# Добавляем диалог-группу в базу:
	Bot.addDialogueGroup(
		DialogueGroup(query.message.chat, VK_ID)
	)

	# Отправляем сообщение:
	await query.message.edit_text(f"<b>Отлично! 😌</b>\n\nТы выбрал диалог с <b>«{dialogue.fullName}»</b>, теперь все сообщения от <b>{dialogue.fullName}</b> будут появляться именно здесь.\n\n⚙️ Подожди немного, мне необходимо обновить кое-что в этой группе...")

	# Изменяем параметры группы:
	await query.message.chat.set_title(dialogue.fullName)

	try:
		pfpURL: str = "https://vk.com/images/camera_400.png"
		if dialogue.isUser:
			pfpURL = (await user.vkAccount.vkAPI.users.get(user_ids=[dialogue.ID], fields=["photo_max_orig"]))[0].photo_max_orig # type: ignore
		elif dialogue.isGroup:
			pfpURL = (await user.vkAccount.vkAPI.groups.get_by_id(group_id=dialogue.ID, fields=["photo_max_orig"]))[0].photo_max_orig # type: ignore
		else:
			pfpURL = dialogue.photoURL
		
		async with aiohttp.ClientSession() as session:
			async with session.get(pfpURL) as response:
				await query.message.chat.set_photo(InputFile(io.BytesIO(await response.read())))
	except Exception as e:
		logger.error("Не удалось загрузить картинку профиля: %s", e)

	try:
		await query.message.chat.set_description(f"[Telehooper] Диалог с {dialogue.fullName}.")
	except: pass


	return await query.answer()

# coding: utf-8

"""Обработчик для команды `This`."""

import asyncio
import io
from typing import Tuple

import aiogram
import aiohttp
from aiogram import Dispatcher
from aiogram.types import (CallbackQuery, Chat, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from aiogram.types import Message as MessageType
from aiogram.types import User
from Consts import CommandThrottleNames as CThrottle
from Consts import InlineButtonCallbacks as CButton
from DB import getDefaultCollection
from Exceptions import CommandAllowedOnlyInGroup
from loguru import logger
from ServiceAPIs.Base import DialogueGroup
from TelegramBot import Telehooper, TelehooperUser

TELEHOOPER:	Telehooper = None # type: ignore
DP: 		Dispatcher = None # type: ignore


def _setupHandler(bot: Telehooper) -> None:
	"""
	Инициализирует Handler.
	"""

	global TELEHOOPER, DP

	TELEHOOPER = bot
	DP = TELEHOOPER.DP

	DP.register_message_handler(This, commands=["this", "thischat", "chat", "dialogue"])
	DP.register_callback_query_handler(ThisCallbackHandler, lambda query: query.data == CButton.CommandCallers.THIS)
	DP.register_callback_query_handler(DialogueConvertMenuCallback, lambda query: query.data == CButton.CommandCallers.CONVERT)
	DP.register_callback_query_handler(ConvertGroupToDialogueCallback, lambda query: query.data == CButton.CommandActions.CONVERT_TO_DIALOGUE)
	DP.register_callback_query_handler(VKDialogueSelector, lambda query: query.data.startswith(CButton.CommandActions.DIALOGUE_SELECT_VK))
	DP.register_callback_query_handler(ConvertDialogueToGroupCallback, lambda query: query.data == CButton.CommandActions.CONVERT_TO_REGULAR_GROUP)


async def This(msg: MessageType):
	if msg.chat.type == "private":
		raise CommandAllowedOnlyInGroup()

	# await DP.throttle(CThrottle.THIS_DIALOGUE, rate=30, user_id=msg.from_user.id)

	user = await TELEHOOPER.getBotUser(msg.from_user.id)
	dialogue = await user.getDialogueGroupByTelegramGroup(msg.chat.id)

	# Если в диалоге:
	if dialogue:
		await ThisDialogue(msg, user)
		return

	# Если в обычной группе:
	await ThisGroup(msg)

async def ThisDialogue(msg: MessageType, user: TelehooperUser) -> None:
	"""
	Вызывается в диалогах.
	"""

	dialogue = await user.getDialogueGroupByTelegramGroup(msg.chat.id)

	assert dialogue is not None, "Диалог не найден."

	# Создаём ссылку на диалог в ВК:
	DIALOGUE_LINK = "https://vk.com/im?sel="
	if dialogue.serviceDialogueID > 2000000000:
		DIALOGUE_LINK += "c" + str(dialogue.serviceDialogueID - 2000000000)
	else:
		DIALOGUE_LINK += str(dialogue.serviceDialogueID)

	# Клавиатуру:
	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton("🛑 Сконвертировать в обычную группу", callback_data=CButton.CommandActions.CONVERT_TO_REGULAR_GROUP)
	)

	# Мне было лень придумывать метод получения названия диалога из ВК, поэтому я просто брал название чата в Telegram.
	# FIXME: Получение названия чата из ВК.
	await msg.answer(f"<b>Группа-диалог</b> 🫂\n\nДанная группа является диалогом <a href=\"{DIALOGUE_LINK}\">{msg.chat.full_name}</a>. Все сообщения, отправляемые тут, будут отправляться в диалог <a href=\"{DIALOGUE_LINK}\">{msg.chat.full_name}</a>.\nДанный диалог можно вернуть в состояние обычной группы, если нажать на кнопку ниже:", reply_markup=keyboard)

async def ThisGroup(msg: MessageType, edit_message_instead: bool = False):
	"""
	Вызывается в группах.
	"""

	_text = f"<b>Группа-диалог 🫂\n\n</b>На данный момент, группа <b>«{msg.chat.full_name}»</b> не является диалогом сервиса. Что бы преобразовать группу в диалог, воспользуйся кнопкой ниже.\n\n⚙️ Преобразуй группу в диалог, нажав на кнопку ниже:"

	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton(text="♻️ Конвертировать", callback_data=CButton.CommandCallers.CONVERT)
	)

	if edit_message_instead:
		await msg.edit_text(_text, reply_markup=keyboard)
		return

	await msg.answer(_text, reply_markup=keyboard)

async def ThisCallbackHandler(query: CallbackQuery):
	"""Кнопка назад."""

	await ThisGroup(query.message, True)

async def ConvertToDialogueMessage(msg: MessageType, edit_message_instead: bool = False) -> None:
	"""
	Отправляет сообщение со всеми условиями. Это сообщение должно отправляться лишь одинажды.
	"""

	CONDITIONS_MET = await CheckServiceDialogueConversionConditions(msg.chat, msg.from_user)
	ALL_CONDITIONS_ARE_MET = all(CONDITIONS_MET)

	_text = f"""<b>⚠️ Предупреждение! Потенциально разрушительная команда! ⚠️</b>

Прямо сейчас, ты пытаешься провести акт перевода <b>Telegram-группы</b> в <b>диалог сервиса</b>. Это значит, что под конкретного пользователя/беседу подключённого сервиса можно сделать отдельный диалог в <b>Telegram.
</b>Пожалуйста, <b>внимательно прочитай</b> следующее сообщение, оно будет показано лишь <b>раз</b>.

<b>ℹ️ Существуют некоторые лимиты:</b>
    <b>•</b> <b>1</b> диалог подключённого сервиса — <b>1 группа</b>,
    <b>•</b> Лимит Telegram по количеству групп — <b>500 штук</b> (<a href=\"https://limits.tginfo.me/ru-RU\">клик</a>),
    <b>•</b> В день можно создавать <b>50 групп</b> (<a href=\"https://limits.tginfo.me/ru-RU\">клик</a>),
    <b>•</b> В группе не может быть более 20 ботов (<a href="https://limits.tginfo.me/ru-RU">клик</a>).

<b>ℹ️ После конвертирования у группы изменится:</b>
    <b>•</b> Название; на имя диалога,
    <b>•</b> Фотография; на фото диалога,
    <b>•</b> Описание,
    <b>•</b> Закреплённые сообщения будут откреплены.

✍️ {"Все следующие условия для преобразования группы были соблюдены" if ALL_CONDITIONS_ARE_MET else "Продолжить можно, если выполнить все следующие <b>условия</b> для преобразования группы"}:
    {"✅" if CONDITIONS_MET[0] else "☑️"} Ты должен быть администратором в группе,
    {"✅" if CONDITIONS_MET[1] else "☑️"} У бота должны права администратора,
    {"✅" if CONDITIONS_MET[2] else "☑️"} Данная группа не должна уже быть диалогом.

⚙️ {"Если ты согласен, то нажми на кнопку ниже:" if ALL_CONDITIONS_ARE_MET else "<b>Продолжить можно после выполнения всех условий, описанных выше❗️</b>"}
"""

	keyboard = InlineKeyboardMarkup()

	if ALL_CONDITIONS_ARE_MET:
		keyboard.add(
			InlineKeyboardButton("⚙️ Конвертировать", callback_data=CButton.CommandActions.CONVERT_TO_DIALOGUE)
		)

	keyboard.insert(
		InlineKeyboardButton("🔙 Отмена", callback_data=CButton.CommandCallers.THIS)
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
	NOT_CONNECTED_AS_DIALOGUE: bool = True # TODO: сделать проверку на наличие диалога в базе

	# Получаем список админов в чате:
	chat_admins = (await TELEHOOPER.TGBot.get_chat_administrators(chat.id))

	USER_SENDER_IS_ADMIN = bool([i for i in chat_admins if i.user.id == user.id])
	BOT_IS_ADMIN = bool([i for i in chat_admins if i.user.id == TELEHOOPER.TGBot.id])

	return (
		USER_SENDER_IS_ADMIN,
		BOT_IS_ADMIN,
		NOT_CONNECTED_AS_DIALOGUE
	)

async def DialogueConvertMenuCallback(query: CallbackQuery):
	# Проверяем, нужно ли отправлять сообщение с условиями преобразования группы в диалог:
	DB = getDefaultCollection()

	res = DB.find_one({"_id": query.from_user.id})
	if res is None or res["IsAwareOfDialogueConversionConditions"] is False:
		await ConvertToDialogueMessage(query.message, True)

		return

	# Пользователь уже встречался с предупредительным сообщением, поэтому его отправлять снова не нужно.

	CONDITIONS_MET = await CheckServiceDialogueConversionConditions(query.message.chat, query.message.from_user)
	ALL_CONDITIONS_ARE_MET = all(CONDITIONS_MET)

	if not ALL_CONDITIONS_ARE_MET:
		return await query.answer("Ошибка ⚠️\n\n1. У тебя есть права админа?\n2. У этого бота есть права админа?", True)

	await ConvertGroupToDialogueCallback(query)

async def DialogueMenuCallback(query: CallbackQuery) -> None:
	"""Кнопка назад."""

	await ConvertToDialogueMessage(query.message, True)

async def ConvertGroupToDialogueCallback(query: CallbackQuery) -> None:
	"""
	Переводит группу в диалог.
	"""

	# Сохраняем, что пользователь уже ознакомился с угрозами преобразования группы в диалог:
	DB = getDefaultCollection()
	DB.update_one({"_id": query.from_user.id}, {"$set": {"IsAwareOfDialogueConversionConditions": True}})

	# Делаем группу "пустой":
	await MakeGroupEmpty(query.message.chat)

	# Я не хочу что бы сообщения о успешном конвертировании в диалог оказались до Telegram-овских сообщений о "Telehooper удалил фото группы":
	await asyncio.sleep(0.5)

	# Отправляем сообщение о успешном конвертировании, после чего начинаем грузить чаты ВКонтакте:
	_text = "<b>Перевод группы в диалог 🫂\n\nУспешно!</b> Группа была успешно конвертирована в <b>диалог</b>. Теперь тебе необходимо выбрать, к какому именно диалогу эта группа будет подключена. Если, к примеру, выбрать диалог с <a href=\"http://vk.com/durov\">Павлом Дуровым</a>, то все сообщения от него будут появляться <b>именно здесь</b>, и отвечать на них ты будешь тут же.\n\n"

	# Создаём несколько кнопок, что бы чат не прыгал после загрузки чатов:
	keyboard = InlineKeyboardMarkup()
	for i in range(12):
		keyboard.add(InlineKeyboardButton("загрузка...", callback_data=CButton.DO_NOTHING))

	await query.message.edit_text(f"{_text}⏳ Пожалуйста, подожди, пока я загружаю список диалогов <b>ВКонтакте</b>...", disable_web_page_preview=True, reply_markup=keyboard)

	# Грузим чаты ВК. Получаем объект пользователя:
	user = await TELEHOOPER.getBotUser(query.from_user.id)

	# Получаем список всех диалогов:
	user_convos = await TELEHOOPER.vkAPI.retrieveDialoguesList(user) # type: ignore

	# Для эмодзи перед названием диалога:
	prefixEmojiDict = {
		"group": "🫂",
		"user_True": "🙋‍♂️", # Эмодзи мужчины
		"user_False": "🙋‍♀️", # Эмодзи женщины
		"chat": "💬",
	}

	keyboard = InlineKeyboardMarkup()
	for index, convo in enumerate(user_convos):
		if index > 12:
			# Если что-то пойдет не так, и юзер слишком уж общительный, и
			# имеет больше чем 12 человек в своих диалогах, то
			# просто прекращаем работу цикла, иначе бот ответит миллиардом кнопок.

			break

		if convo.isSelf:
			# Пропускаем диалог с самим собой (Избранное)

			continue

		buttonText = f"{prefixEmojiDict[(convo._type + '_' + str(convo.isMale)) if convo.isUser else convo._type]} {convo.fullName} {'📌' if convo.isPinned else ''}"

		keyboard.add(InlineKeyboardButton(buttonText, callback_data=CButton.CommandActions.DIALOGUE_SELECT_VK + str(convo.ID)))


	await query.message.edit_text(f"{_text}⚙️ Выбери любой нужный диалог из <b>ВКонтакте</b>:", reply_markup=keyboard, disable_web_page_preview=True)

async def VKDialogueSelector(query: CallbackQuery) -> bool:
	VK_ID = int(query.data.split(CButton.CommandActions.DIALOGUE_SELECT_VK)[-1])

	# TODO: Сделать проверку, вдруг такой чат уже был подключён к диалогу. Если да, то отключить предыдущий чат (сделать пустым).

	# Получаем информацию:
	user = await TELEHOOPER.getBotUser(query.from_user.id)

	# Проверяем, не является ли группа диалогом:
	if await user.getDialogueGroupByTelegramGroup(query.message.chat.id):
		return await query.answer("Эта группа уже является диалогом.")

	dialogue = TELEHOOPER.vkAPI.getDialogueByID(user, VK_ID) # type: ignore
	if not dialogue:
		return await query.answer("Произошла ошибка, выполни команду снова.")

	# Отправляем сообщение:
	await query.message.edit_text(f"<b>Группа-диалог</b> 🫂\n\nТы выбрал диалог с <b>«{dialogue.fullName}»</b>, теперь все сообщения от <b>{dialogue.fullName}</b> будут появляться именно здесь.\n\n⏳ Подожди немного, мне необходимо обновить кое-что в этой группе...")

	# Изменяем параметры группы.
	# Отправляем сообщение-закреп:
	pinnedMessage = await query.message.answer("<i>В этом сообщении будет управление диалогом, WIP</i>")
	await pinnedMessage.pin(disable_notification=True)

	# Название чата:
	await query.message.chat.set_title(dialogue.fullName)

	# Загружаем фотку:
	try:
		pfpURL: str = "https://vk.com/images/camera_400.png"
		if dialogue.isUser:
			pfpURL = (await user.vkAPI.users.get(user_ids=[dialogue.absID], fields=["photo_max_orig"]))[0].photo_max_orig # type: ignore
		elif dialogue.isGroup:
			pfpURL = (await user.vkAPI.groups.get_by_id(group_id=dialogue.absID, fields=["photo_max_orig"]))[0].photo_max_orig # type: ignore
		else:
			pfpURL = dialogue.photoURL or "https://vk.com/images/camera_400.png"

		async with aiohttp.ClientSession() as session:
			async with session.get(pfpURL) as response:
				await query.message.chat.set_photo(
					aiogram.types.InputFile(
						io.BytesIO(
							await response.read()
						)
					)
				)
	except Exception as error:
		logger.error(f"Не удалось загрузить картинку профиля: {error}")

	# Меняем описание диалога:
	try:
		await query.message.chat.set_description(f"[Telehooper] Диалог с {dialogue.fullName}.")
	except:
		pass

	# Добавляем диалог-группу в базу:
	TELEHOOPER.addDialogueGroup(
		DialogueGroup(
			await TELEHOOPER.TGBot.get_chat(query.message.chat.id),
			VK_ID,
			user.TGUser.id
		)
	)

	# Отправляем сообщения о успешной конвертации.
	await query.message.answer(f"<b>Группа-диалог</b> 🫂\n\nПрекрасно! Эта группа теперь является диалогом с <b>«{dialogue.fullName}»</b>! Все сообщения, отправляемые здесь, будут отправляться в диалог. Настроить этот диалог можно снова воспользовавшись командой /this.\nПриятного общения! 😊")


	return await query.answer()

async def MakeGroupEmpty(chat: Chat):
	"""
	Делает группу "пустой". Используется при конвертировании группы в диалог, ...
	"""

	# Переводим группу в диалог, удаляем фото группы, ...
	await chat.set_title("ㅤ")

	# Удаляем фото группы:
	try:
		await chat.delete_photo()
	except: pass

	# Меняем описание группы:
	try:
		await chat.set_description("[Telehooper] Пустой диалог сервиса.")
	except: pass

	# Убираем все закрепы:
	await chat.bot.unpin_all_chat_messages(chat.id)

async def ConvertDialogueToGroupCallback(query: CallbackQuery):
	"""
	Преобразовывает диалог сервиса в Telegram-группу.
	"""

	# Очищаем группу:
	await MakeGroupEmpty(query.message.chat)

	# TODO: Удаляем запись в ДБ:
	DB = getDefaultCollection()
	DB.update_one(
		{
			"_id": "_global"
		}, 
		
		{
			"$pull": {
				"ServiceDialogues.VK": {
					"TelegramGroupID": query.message.chat.id
				}
			}
		}
	)

	# Меняем сообщение, попутно пряча кнопки.
	await query.message.edit_text("<b>Группа-диалог 🫂\n\n</b>Данная группа больше <b>не является</b> диалогом. Ты можешь с легкостью преобразовать эту или любую другую группу в диалог, воспользовавшись командой /this.")

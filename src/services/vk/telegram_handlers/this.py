# coding: utf-8

import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Text
from aiogram.types import (BotCommand, BotCommandScopeChatAdministrators,
                           CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, User)

import utils
from api import TelehooperAPI
from services.vk.consts import VK_GROUP_DIALOGUE_COMMANDS


router = Router()

DIALOGUES_PER_PAGE = 10

@router.callback_query(Text("/this vk"), F.message.as_("msg"))
async def this_vk_inline_handler(query: CallbackQuery, msg: Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем кнопки "ВКонтакте" в команде `/this`.
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="🔙 Назад", callback_data="/this")],

		[InlineKeyboardButton(text="💬 Сообщения и общаться", callback_data="/this vk messages")],
		[InlineKeyboardButton(text="[wip] 🗞 Новости/посты из групп", callback_data="/this vk posts")],
	])

	await TelehooperAPI.edit_or_resend_message(
		"<b>🫂 Группа-диалог — ВКонтакте</b>.\n"
		"\n"
		"В данный момент, Вы пытаетесь соединить данную группу Telegram с сообществом либо же диалогом ВКонтакте.\n"
		"Ответив на вопросы бот определит, какую роль будет выполнять данная группа.\n"
		"\n"
		"<b>❓ Что Вы хотите получать из ВКонтакте</b>?",
		message_to_edit=msg,
		chat_id=msg.chat.id,
		reply_markup=keyboard,
		query=query
	)

@router.callback_query(Text("/this vk messages"), F.message.as_("msg"))
async def this_vk_messages_inline_handler(query: CallbackQuery, msg: Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем кнопку "Хочу получать сообщения и общаться" в команде `/this`.
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="🔙 Назад", callback_data="/this vk")],

		# [InlineKeyboardButton(text="👥 Telegram-группа для всех чатов ВК", callback_data="do-nothing")],
		[InlineKeyboardButton(text="👤 Один чат ВК - одна Telegram-группа", callback_data="/this vk messages separated selection")],
	])

	await TelehooperAPI.edit_or_resend_message(
		"<b>🫂 Группа-диалог — ВКонтакте — сообщения</b>.\n"
		"\n"
		"Вы пытаетесь получать <b>сообщения</b> из ВКонтакте. Если Вы ошиблись с выбором, то нажмите на кнопку «назад».\n"
		"Следующий вопрос:\n"
		"\n"
		"<b>❓ Как Вам будет удобно получать сообщения</b>?\n"
		"\n"
		"ℹ️ Вы не создали «общую» группу в Telegram, рекомендуется выбрать «Telegram-группа для всех чатов». Без такой группы Telehooper не сможет отправлять сообщения от новых людей.", # TODO: Проверка на это.
		message_to_edit=msg,
		chat_id=msg.chat.id,
		reply_markup=keyboard,
		query=query
	)

@router.callback_query(Text("/this vk posts"), F.message.as_("msg"))
async def this_vk_posts_inline_handler(query: CallbackQuery, msg: Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем кнопку "Хочу читать новости/посты из групп" в команде `/this`.
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="🔙 Назад", callback_data="/this vk")],

		# [InlineKeyboardButton(text="🗞 Все новости в одной Telegram-группе", callback_data="do-nothing")],
		# [InlineKeyboardButton(text="🫂 Одно сообщество ВК - одна Telegram-группа", callback_data="do-nothing")],
	])

	await TelehooperAPI.edit_or_resend_message(
		"<b>🫂 Группа-диалог — ВКонтакте — посты/новости</b>.\n"
		"\n"
		"Вы пытаетесь получать <b>посты или новости</b> из ВКонтакте. Если Вы ошиблись с выбором, то нажмите на кнопку «назад».\n"
		"Следующий вопрос:\n"
		"\n"
		"<b>❓ Как именно Вы хотите получать посты или новости</b>?",
		message_to_edit=msg,
		chat_id=msg.chat.id,
		reply_markup=keyboard,
		query=query
	)

@router.callback_query(Text(startswith="/this vk messages separated"), F.message.as_("msg"), F.from_user.as_("user"), F.data.as_("queryStr"))
async def this_vk_messages_separated_inline_handler(query: CallbackQuery, msg: Message, user: User, queryStr: str) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем на кнопку "Хочу читать новости/посты из групп" в команде `/this`.
	"""

	# TODO: Возможность написать юзеру в ВК через никнейм/ссылку.

	telehooper_user = await TelehooperAPI.get_user(user)
	vkServiceAPI = telehooper_user.get_vk_connection()

	assert vkServiceAPI is not None, "Сервис ВКонтакте не существует"

	is_forced_update = queryStr.endswith("forced")
	will_load_chats = is_forced_update or not vkServiceAPI.has_cached_list_of_dialogues()

	if will_load_chats:
		loading_buttons = []
		for i in range(DIALOGUES_PER_PAGE):
			loading_buttons.append([InlineKeyboardButton(text="⏳ загрузка...", callback_data="do-nothing")])

		keyboard = InlineKeyboardMarkup(inline_keyboard=[
			[InlineKeyboardButton(text="ㅤ", callback_data="do-nothing")],

			*loading_buttons,

			[InlineKeyboardButton(text="ㅤ", callback_data="do-nothing")]
		])

		await TelehooperAPI.edit_or_resend_message(
			"<b>🫂 Группа-диалог — ВКонтакте — сообщения</b>.\n"
			"\n"
			"Вы собираетесь создать отдельную группу для отдельного чата из ВКонтакте. После выбора чата, бот сделает данную группу похожей на выбранный диалог ВКонтакте.\n"
			"\n"
			"<i>⏳ Пожалуйста, дождитесь получения списка чатов...</i>",
			message_to_edit=msg,
			chat_id=msg.chat.id,
			reply_markup=keyboard,
			query=query
		)

	# Получаем список диалогов, а так же спим что бы бот "работал" 5 секунд,
	# и пользователи не могли уж слишком часто перезагружать список диалогов,
	# нагружая бота, а так же API ВКонтакте, повышая шанс на получение captcha.
	start_time = asyncio.get_running_loop().time()
	dialogues = await vkServiceAPI.get_list_of_dialogues(force_update=is_forced_update, max_amount=200, skip_ids=[vkServiceAPI.service_user_id])
	if will_load_chats:
		await asyncio.sleep(5 - (asyncio.get_running_loop().time() - start_time))

	# Создаём кучку кнопок под диалоги.
	dialogues_kbd = []

	dialogues_shown = len(dialogues)
	last_page = dialogues_shown // DIALOGUES_PER_PAGE + 1

	current_page = 1
	if "page" in (queryStr or ""):
		current_page = utils.clamp(int(queryStr.split(" ")[-1]), 1, last_page)

	for dialogue in dialogues[(current_page - 1) * DIALOGUES_PER_PAGE : current_page * DIALOGUES_PER_PAGE]:
		prefix = "👥" if dialogue.is_multiuser else ""
		name = dialogue.name
		postfix = f"{(str(dialogue.incoming_messages) + ' входящих ✉️') if dialogue.incoming_messages else ''}   {'📌' if dialogue.is_pinned else ''} {'🔕' if dialogue.is_muted else ''}".strip()

		dialogues_kbd.append([InlineKeyboardButton(text=f"{prefix}  {name}  {postfix}".strip(), callback_data=f"/this vk convert {dialogue.id} messages separated")])

	# Создаём клавиатуру с диалогами.
	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[
			InlineKeyboardButton(text="🔙 Назад", callback_data="/this vk messages"),
			InlineKeyboardButton(text="🔄 Обновить", callback_data="/this vk messages separated forced"),
		],

		*dialogues_kbd,

		[
			InlineKeyboardButton(text="⏪", callback_data="do-nothing" if current_page == 1 else "/this vk messages separated page 1"),
			InlineKeyboardButton(text="◀️", callback_data="do-nothing" if current_page == 1 else f"/this vk messages separated page {current_page - 1}"),
			InlineKeyboardButton(text=f"{current_page} / {last_page}", callback_data="do-nothing"),
			InlineKeyboardButton(text="▶️", callback_data="do-nothing" if current_page == last_page else f"/this vk messages separated page {current_page + 1}"),
			InlineKeyboardButton(text="⏩", callback_data="do-nothing" if current_page == last_page else f"/this vk messages separated page {last_page}"),
		] if dialogues_shown > DIALOGUES_PER_PAGE else [],
	])

	await TelehooperAPI.edit_or_resend_message(
		"<b>🫂 Группа-диалог — ВКонтакте — сообщения</b>.\n"
		"\n"
		"Вы собираетесь создать отдельную группу для отдельного чата из ВКонтакте. После выбора чата, бот сделает данную группу похожей на выбранный диалог ВКонтакте.\n"
		f"Чатов отображено — {dialogues_shown} штук.\n",
		message_to_edit=msg,
		chat_id=msg.chat.id,
		reply_markup=keyboard,
		query=query
	)

@router.callback_query(Text(startswith="/this vk convert"), F.message.as_("msg"), F.from_user.as_("user"), F.data.as_("queryStr"))
async def this_vk_convert_inline_handler(query: CallbackQuery, msg: Message, user: User, queryStr: str) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии выборе диалога/группы в команде `/this` для ВКонтакте.
	"""

	splitted = queryStr.split()

	chat_id = int(splitted[3])
	is_messages = "messages" in splitted
	is_separated = "separated" in splitted

	assert is_messages
	assert is_separated

	telehooper_user = await TelehooperAPI.get_user(user)
	telehooper_group = await TelehooperAPI.get_group(telehooper_user, msg.chat)
	vkServiceAPI = telehooper_user.get_vk_connection()
	bot = Bot.get_current()

	assert telehooper_group is not None, "Группа не существует"
	assert vkServiceAPI is not None, "Сервис ВКонтакте не существует"
	assert bot is not None, "Telegram-бот не существует"

	dialog = await vkServiceAPI.get_service_dialogue(chat_id)

	assert dialog is not None, "Диалог не существует"

	# Проверка на то, что такой диалог уже существует.
	if TelehooperAPI.get_subgroup_by_service_dialogue(telehooper_user, dialog):
		await query.answer(
			"Упс, этот диалог уже подключён к боту.\n"
			"\n"
			"ℹ️ Воспользуйтесь командой /me, что бы найти группу, с которой этот диалог связан.",
			show_alert=True
		)

		return

	await TelehooperAPI.edit_or_resend_message(
		"<b>🫂 Группа-диалог — ВКонтакте — сообщения</b>.\n"
		"\n"
		f"Отлично! Вы выбрали чат с «{dialog.name}».\n"
		"Дождитесь, пока Telehooper сделает свою магию... 👀\n"
		"\n"
		"<i>⏳ Пожалуйста, подождите, пока Telehooper превращает данную Telegram-группу в похожий диалог из ВКонтакте...</i>",
		message_to_edit=msg,
		chat_id=msg.chat.id,
		query=query
	)

	# TODO: Проверка на права админа у бота.
	# TODO: Проверка на права админа у юзера?
	# TODO: Сделать настройку, а так же извлечение текста закрепа из диалога ВКонтакте, сделав его закрепом в Telegram.
	# TODO: Сделать настройку, а так же пересылку последних сообщений в диалоге.

	await telehooper_group.convert_to_dialogue_group(telehooper_user, dialog, msg, vkServiceAPI)

	# Изменяем список команд.
	await bot.set_my_commands(
		commands=[BotCommand(command=command, description=description) for command, description in VK_GROUP_DIALOGUE_COMMANDS.items()],
		scope=BotCommandScopeChatAdministrators(type="chat_administrators", chat_id=msg.chat.id)
	)

	await asyncio.sleep(2)

	docs_url = "https://github.com/Zensonaton/Telehooper/blob/rewrite/src/services/vk/README.md"
	docs_info = [
		"Учтите следующее:",
		" • Реакции не поддерживаются.",
		" • «Прочитать» сообщения можно через <code>/read</code>.",
		" • Удалять сообщения можно только через <code>/delete</code>."
	]

	if dialog.is_multiuser:
		docs_info.append(" • Все сообщения будут иметь префикс вида [<b>Имя Фамилия</b>].")

	if await telehooper_user.get_setting("Services.VK.SetOnline"):
		docs_info.append(" • Вы будете «онлайн» после отправки сообщения (см. {{Services.VK.SetOnline}}).")
	else:
		docs_info.append(" • Вы никогда не появитесь «онлайн» ВКонтакте (см. {{Services.VK.SetOnline}}).")

	if await telehooper_user.get_setting("Services.VK.WaitToType"):
		docs_info.append(" • Бот будет «печатать» в ВК перед пересылкой Вашего сообщения (см. {{Services.VK.WaitToType}}).")
	else:
		docs_info.append(" • Собеседник не будет видеть Вашу печать (см. {{Services.VK.WaitToType}}).")

	docs_info.append(f" • Другие ограничения и примечания можно прочитать <a href=\"{docs_url}\">здесь</a>.")

	if (dialog.multiuser_count or 0) >= 3:
		docs_info.append("")
		docs_info.append(f"Поскольку Вы подключили беседу в которой находится {dialog.multiuser_count} участников, Вам может быть неудобно воспринимать сообщения. В будущем, у Telehooper появится настройка, что бы Вы смогли добавлять кучу «мини-ботов», от имени которых будут отправляться сообщения. Следите за обновлениями бота!")

	docs_info_str = "\n".join(docs_info)

	await msg.answer(utils.replace_placeholders(
		"<b>✅ Группа-диалог — успех</b>.\n"
		"\n"
		"Telehooper успешно подключил диалог ВКонтакте.\n"
		f"Теперь, все сообщения, которые Вы отправляете сюда, будут пересылаться в диалог «{dialog.name}» ВКонтакте и наоборот.\n"
		"\n"
		f"{docs_info_str}\n"
		"\n"
		"<b>Приятного общения! 😊</b>"
		),
		disable_web_page_preview=True
	)

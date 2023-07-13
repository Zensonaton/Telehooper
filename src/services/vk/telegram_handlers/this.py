# coding: utf-8

import asyncio
from typing import cast

from aiogram import F, Router, types, Bot
from aiogram.filters import Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChatAdministrators
from services.vk.consts import VK_GROUP_DIALOGUE_COMMANDS

import utils
from api import TelehooperAPI


router = Router()

DIALOGUES_PER_PAGE = 10

@router.callback_query(Text("/this vk"), F.message.as_("msg"))
async def this_vk_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем кнопки "ВКонтакте" в команде `/this`.
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="🔙 Назад", callback_data="/this")],

		[InlineKeyboardButton(text="💬 Сообщения и общаться", callback_data="/this vk messages")],
		[InlineKeyboardButton(text="[wip] 🗞 Новости/посты из групп", callback_data="/this vk posts")],
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

		# [InlineKeyboardButton(text="👥 Telegram-группа для всех чатов ВК", callback_data="do-nothing")],
		[InlineKeyboardButton(text="👤 Один чат ВК - одна Telegram-группа", callback_data="/this vk messages separated selection")],
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

		# [InlineKeyboardButton(text="🗞 Все новости в одной Telegram-группе", callback_data="do-nothing")],
		# [InlineKeyboardButton(text="🫂 Одно сообщество ВК - одна Telegram-группа", callback_data="do-nothing")],
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

@router.callback_query(Text(startswith="/this vk messages separated"), F.message.as_("msg"))
async def this_vk_messages_separated_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии пользователем на кнопку "Хочу читать новости/посты из групп" в команде `/this`.
	"""

	# TODO: Возможность написать юзеру в ВК через никнейм/ссылку.

	assert msg.from_user
	assert query.data

	user = await TelehooperAPI.get_user(query.from_user)
	vkServiceAPI = user.get_vk_connection()
	assert vkServiceAPI is not None, "Сервис ВКонтакте не существует"

	is_forced_update = cast(str, query.data).endswith("forced")
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

		await msg.edit_text(
			"<b>🫂 Группа-диалог — ВКонтакте — сообщения</b>.\n"
			"\n"
			"Вы собираетесь создать отдельную группу для отдельного чата из ВКонтакте. После выбора чата, бот сделает данную группу похожей на выбранный диалог ВКонтакте.\n"
			"\n"
			"<i>⏳ Пожалуйста, дождитесь получения списка чатов...</i>",
			reply_markup=keyboard
		)

	# Получаем список диалогов, а так же спим что бы бот "работал" 5 секунд,
	# и пользователи не могли уж слишком часто перезагружать список диалогов,
	# нагружая бота, а так же API ВКонтакте, повышая шанс на получение captcha.
	start_time = asyncio.get_running_loop().time()
	dialogues = await vkServiceAPI.get_list_of_dialogues(
		retrieve_all=True,
		force_update=is_forced_update,
		skip_ids=[
			vkServiceAPI.service_user_id
		]
	)
	if will_load_chats:
		await asyncio.sleep(5 - (asyncio.get_running_loop().time() - start_time))

	# Создаём кучку кнопок под диалоги.
	dialogues_kbd = []

	total_dialogues = len(dialogues)
	last_page = total_dialogues // DIALOGUES_PER_PAGE + 1

	current_page = 1
	if "page" in (query.data or ""):
		current_page = utils.clamp(
			int(query.data.split(" ")[-1]),
			1,
			last_page
		)


	for dialogue in dialogues[(current_page - 1) * DIALOGUES_PER_PAGE : current_page * DIALOGUES_PER_PAGE]:
		prefix = "👥" if dialogue.is_multiuser else ""
		name = dialogue.name
		postfix = f"{'📌' if dialogue.is_pinned else ''} {'🔕' if dialogue.is_muted else ''}"

		dialogues_kbd.append([
			InlineKeyboardButton(
				text=f"{prefix}  {name}  {postfix}", callback_data=f"/this vk convert {dialogue.id} messages separated"
			)
		])

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
		] if total_dialogues > DIALOGUES_PER_PAGE else [],
	])

	await msg.edit_text(
		"<b>🫂 Группа-диалог — ВКонтакте — сообщения</b>.\n"
		"\n"
		"Вы собираетесь создать отдельную группу для отдельного чата из ВКонтакте. После выбора чата, бот сделает данную группу похожей на выбранный диалог ВКонтакте.\n"
		f"Всего чатов ВКонтакте у Вас — {total_dialogues} штук.\n"
		"\n"
		"ℹ️ Нужно написать человеку с которым ещё ни разу не общались? Отправьте ссылку/никнейм человека из ВКонтакте сюда.",
		reply_markup=keyboard
	)

@router.callback_query(Text(startswith="/this vk convert"), F.message.as_("msg"))
async def this_vk_convert_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии выборе диалога/группы в команде `/this` для ВКонтакте.
	"""

	assert query.data

	splitted = query.data.split()

	chat_id = int(splitted[3])
	is_messages = "messages" in splitted
	is_separated = "separated" in splitted

	assert is_messages
	assert is_separated

	user = await TelehooperAPI.get_user(query.from_user)
	group = await TelehooperAPI.get_group(msg.chat)
	vkServiceAPI = user.get_vk_connection()
	bot = Bot.get_current()

	assert group is not None, "Группа не существует"
	assert vkServiceAPI is not None, "Сервис ВКонтакте не существует"
	assert bot is not None, "Telegram-бот не существует"

	dialog = await vkServiceAPI.get_dialogue(chat_id)

	assert dialog is not None, "Диалог не существует"

	await msg.edit_text(
		"<b>🫂 Группа-диалог — ВКонтакте — сообщения</b>.\n"
		"\n"
		f"Отлично! Вы выбрали чат с «{dialog.name}».\n"
		"Дождитесь, пока Telehooper сделает свою магию... 👀\n"
		"\n"
		"<i>⏳ Пожалуйста, подождите, пока Telehooper превращает данную Telegram-группу в похожий диалог из ВКонтакте...</i>"
	)

	# TODO: Проверка на права админа у бота.
	# TODO: Права на права админа у юзера?
	# TODO: Сделать настройку, а так же извлечение текста закрепа из диалога ВКонтакте, сделав его закрепом в Telegram.

	await asyncio.sleep(3)
	await group.convert_to_dialogue_group(user, dialog, msg)

	# Изменяем список команд.
	await bot.set_my_commands(
		commands=[
			BotCommand(
				command=command,
				description=description
			) for command, description in VK_GROUP_DIALOGUE_COMMANDS.items()
		],
		scope=BotCommandScopeChatAdministrators(
			type="chat_administrators",
			chat_id=msg.chat.id
		)
	)

	await asyncio.sleep(2)
	await msg.answer(
		"<b>✅ Группа-диалог — успех</b>.\n"
		"\n"
		"Telehooper успешно конвертировал данную Telegram-группу в диалог из ВКонтакте.\n"
		f"Теперь, все сообщения, которые Вы отправляете сюда, будут отправляться в диалог «{dialog.name}» из ВКонтакте и наоборот.\n"
		"\n"
		"Однако, учтите что есть следующие ограничения:\n"
		" • Отсутствует поддержка реакций.\n"
		" • Ваш собеседник не видит как Вы печатаете.\n"
		" • Помечать сообщения как «прочитанные» можно только через /read.\n"
		" • Удалять сообщения можно только через /delete.\n"
		"Подробная информация про ограничения: <a href=\"https://github.com/Zensonaton/Telehooper/blob/rewrite/src/services/vk/README.md\">🔗 ссылка</a>.\n"
		"\n"
		"<b>Приятного общения! 😊</b>",
		disable_web_page_preview=True
	)

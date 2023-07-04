# coding: utf-8

from aiogram import Bot, F, Router, types
from aiogram.filters import (ADMINISTRATOR, CREATOR, IS_MEMBER, IS_NOT_MEMBER,
                             JOIN_TRANSITION, MEMBER, RESTRICTED,
                             ChatMemberUpdatedFilter, Text)

from DB import get_db, get_default_group, get_group
from telegram.handlers.this import group_convert_message


router = Router()

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_telehooper_added_in_chat_handler(event: types.ChatMemberUpdated, bot: Bot) -> None:
	"""
	Handler для события добавления бота в группу.

	Отправляет информацию о преобразовании группы в группу-диалог и прочую полезную информацию.
	"""

	# Проверяем, что в группу добавили именно Telehooper.
	if event.new_chat_member.user.id != bot.id:
		return

	keyboard = types.InlineKeyboardMarkup(
		inline_keyboard=[
			[types.InlineKeyboardButton(text="👋 Инструкция по выдаче прав администратора", callback_data="/this showAdminTips")]
		]
	)

	status_message = await bot.send_message(
		chat_id=event.chat.id,
		text=(
			"<b>🫂 Группа-диалог</b>.\n"
			"\n"
			"Что бы продолжить, Вам необходимо <b>выдать мне права администратора</b>. Выдав права администратора мы сможем продолжить выбор диалога.\n"
			"\n"
			"ℹ️ Трудности с выдачей прав администратора? Нажмите на кнопку ниже, чтобы узнать, как это сделать для Вашей платформы.\n"
			"\n"
			"<i>⏳ Данное сообщение отредактируется после получения прав администратора в беседе...</i>"
		),
		reply_markup=keyboard
	)

	# TODO: Проверка что данный объект в БД уже существует.

	db = await get_db()

	group_db = await db.create(
		f"group_{event.chat.id}",
		exists_ok=False,
		data=get_default_group(
			chat=event.chat,
			creator=event.from_user,
			status_message=status_message,
			admin_rights=False # TODO: Случай, если бота каким-то образом добавили в группу, а у него уже есть права админа.
		)
	)
	await group_db.save()

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_other_member_add_handler(event: types.ChatMemberUpdated, bot: Bot) -> None:
	"""
	Handler для случая, если в группу (в котором находится Telehooper) был добавлен какой-то сторонний пользователь.
	"""

	# Добавили иного пользователя в группу.
	if event.new_chat_member.user.is_bot:
		return

	# Проверяем, что это уведомление показано лишь один раз.
	try:
		group = await get_group(event.chat)
	except:
		return

	if group["UserJoinedWarning"]:
		return

	await bot.send_message(
		chat_id=event.chat.id,
		text=(
			"<b>🫂 Группа-диалог</b>\n"
			"\n"
			"Вы добавили иного пользователя в данную группу!\n"
			"Это не запрещено ботом, однако так делать <b>не рекомендуется</b>, поскольку другой пользователь может читать Ваши сообщения, а так же бот может нестабильно работать в случаях присутствия «чужих» пользователей в группе.\n"
			"\n"
			"Будьте осторожны! 🙈"
		)
	)

	# Сохраняем то, что мы предупредили пользователя.
	group["UserJoinedWarning"] = True

	await group.save()

@router.callback_query(Text("/this showAdminTips"), F.message.as_("msg"))
async def show_platform_admin_steps_inline_handler(_: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Handler, вызываемый если пользователь в welcome-сообщении нажал на кнопку с инструкцией по выдаче прав администратора.
	"""

	await msg.edit_text(
		text=(
			"<b>🫂 Группа-диалог</b>.\n"
			"\n"
			"Отлично! Добавив меня в группу, Вы сможете выбрать нужный Вам диалог из подключённого сервиса.\n"
			"\n"
			"Что бы продолжить, Вам необходимо <b>выдать мне права администратора</b>. Выдав права администратора мы сможем продолжить выбор диалога.\n"
			"Инструкции по выдаче прав администратора для разных платформ описаны ниже.\n"
			"\n"
			"Telegram Desktop:\n"
			" • Нажмите на кнопку «Управление группой».\n"
			" • Выберите пункт «Администраторы».\n"
			" • Нажмите на кнопку «Добавить администратора».\n"
			" • Найдите бота @telehooper_bot.\n"
			" • Разрешите всё, кроме пункта «Анонимность».\n"
			"\n"
			"Android:\n"
			" • Откройте список участников группы.\n"
			" • Зажмите палец над этим ботом.\n"
			" • Разрешите всё, кроме пункта «Анонимность».\n"
			"\n"
			"<i>⏳ Данное сообщение отредактируется после получения прав администратора в беседе...</i>"
		)
	)

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=(RESTRICTED | MEMBER) >> (ADMINISTRATOR | CREATOR)))
async def on_admin_promoted_handler(event: types.ChatMemberUpdated):
	# TODO: Убедиться, что данное сообщение будет показано лишь один раз.

	try:
		group = await get_group(event.chat)
	except:
		return

	await group_convert_message(event.chat.id, event.from_user, group["StatusMessageID"], called_from_command=False)

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=(ADMINISTRATOR | CREATOR) >> (RESTRICTED | MEMBER)))
async def on_bot_demotion_handler(event: types.ChatMemberUpdated):
	# TODO: Обработка события, если у бота забрали права администратора.

	...

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_NOT_MEMBER))
async def on_bot_chat_kick_handler(event: types.ChatMemberUpdated):
	# TODO: Обработка события, если бота удалили из группы.

	...

# TODO: Поддержка миграции супергрупп.

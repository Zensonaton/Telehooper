# coding: utf-8

import asyncio

from aiogram import Bot, F, Router, types
from aiogram.filters import (ADMINISTRATOR, CREATOR, IS_MEMBER, IS_NOT_MEMBER,
                             JOIN_TRANSITION, MEMBER, RESTRICTED,
                             ChatMemberUpdatedFilter, Text)
from loguru import logger

import utils
from DB import get_db, get_default_group, get_group
from telegram.handlers.this import group_convert_message


_supergroup_converts = []

router = Router()

async def _supergroup_convert_check(chat_id: int) -> bool:
	"""
	Метод, который проверяет что группа с ID `chat_id` не была недавно конвертирована в supergroup'у.

	Если данный метод вернул True, то нужно пропустить обработку данного события (сделать `return`).
	"""

	# Что бы убедиться, что бот точно получил обновление с конвертацией группы в супергруппу необходимо чуть-чуть поспать.
	await asyncio.sleep(1)

	return chat_id in _supergroup_converts

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_telehooper_added_in_chat_handler(event: types.ChatMemberUpdated, bot: Bot) -> None:
	"""
	Handler для события добавления бота в группу.

	Отправляет информацию о преобразовании группы в группу-диалог и прочую полезную информацию.
	"""

	if event.chat.type == "channel":
		await bot.send_message(
			chat_id=event.chat.id,
			text=(
				"<b>⚠️ Ошибка добавления бота в канал</b>.\n"
				"\n"
				"Упс! Вы добавили бота Telehooper в <b>канал</b>. Telehooper не умеет работать в каналах. 🙈\n"
				"Создайте вместо этого <b>группу</b> и добавьте этого бота в неё.\n"
				"\n"
				"ℹ️ Telehooper автоматически удалит самого себя из данного канала."
			)
		)

		try:
			await bot.leave_chat(chat_id=event.chat.id)
		except:
			pass

		return

	if await _supergroup_convert_check(event.chat.id):
		return

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

	db = await get_db()

	data = get_default_group(
		chat=event.chat,
		creator=event.from_user,
		status_message=status_message,
		topics_enabled=status_message.is_topic_message or False,
		admin_rights=False # TODO: Проверка на наличие прав администратора?
	)

	# Небольшой костыль на случай, если группа уже сохранена в БД бота.
	group_db = await db.create(
		f"group_{event.chat.id}",
		exists_ok=True,
		data=data
	)
	group_db.update(data=data)

	await group_db.save()

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_other_member_add_handler(event: types.ChatMemberUpdated, bot: Bot) -> None:
	"""
	Handler для случая, если в группу (в котором находится Telehooper) был добавлен какой-то сторонний пользователь.
	"""

	if await _supergroup_convert_check(event.chat.id):
		return

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

	await asyncio.sleep(1)

	try:
		group = await get_group(event.chat)
	except:
		return

	# Пытаемся отредактировать сообщение.
	#
	# Если группа была конвертирована в супергруппу, то бот не сможет его отредактировать, поэтому мы его просто отправим.
	try:
		await group_convert_message(event.chat.id, event.from_user, group["StatusMessageID"], called_from_command=False)
	except:
		await group_convert_message(event.chat.id, event.from_user, None, called_from_command=False)

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=(ADMINISTRATOR | CREATOR) >> (RESTRICTED | MEMBER)))
async def on_bot_demotion_handler(event: types.ChatMemberUpdated):
	# TODO: Обработка события, если у бота забрали права администратора.

	...

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_NOT_MEMBER))
async def on_bot_chat_kick_handler(event: types.ChatMemberUpdated):
	# TODO: Обработка события, если бота удалили из группы.

	...

@router.message(F.migrate_to_chat_id)
async def group_to_supergroup_convert_handler(message: types.Message):
	"""
	Handler для события конвертации Telegram-группы в супергруппу.

	При конвертации в супергруппу Telegram меняет ID группы.
	"""

	logger.debug(f"Telegram-группа с ID {message.chat.id} конвертировалась в supergroup'у с ID {message.migrate_to_chat_id}")

	_supergroup_converts.append(message.chat.id)
	_supergroup_converts.append(message.migrate_to_chat_id)

	try:
		group_old = await get_group(message.chat)
	except:
		return

	old_group_data = group_old._data.copy()

	del old_group_data["_id"]
	del old_group_data["_rev"]

	old_group_data["ID"] = message.migrate_to_chat_id
	old_group_data["LastActivityAt"] = utils.get_timestamp()

	db = await get_db()

	# Создаём новый объект группы из БД.
	group_new = await db.create(
		f"group_{message.migrate_to_chat_id}",
		exists_ok=False,
		data=old_group_data
	)

	await group_new.save()

	# Удаляем старый объект группы из БД.
	await group_old.delete()
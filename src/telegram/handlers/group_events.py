# coding: utf-8

import asyncio
from typing import cast

from aiogram import Bot, F, Router
from aiogram.filters import (ADMINISTRATOR, CREATOR, JOIN_TRANSITION, KICKED,
                             LEAVE_TRANSITION, MEMBER, RESTRICTED,
                             ChatMemberUpdatedFilter)
from aiogram.types import (CallbackQuery, ChatMemberUpdated,
                           InlineKeyboardButton, InlineKeyboardMarkup, Message,
                           User)
from cachetools import TTLCache
from loguru import logger

import utils
from api import TelehooperAPI
from DB import get_db, get_default_group, get_group
from telegram.bot import get_minibots
from telegram.handlers.this import group_convert_message


_supergroup_converts = []
_minibot_adds: TTLCache[int, list] = TTLCache(100, 60) # Максимум 100 элементов, 60 секунд хранения.

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
async def on_telehooper_added_in_chat_handler(event: ChatMemberUpdated, bot: Bot) -> None:
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

	status_message = None
	try:
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
			reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👋 Инструкция по выдаче прав администратора", callback_data="/this showAdminTips")]])
		)
	except:
		# Мы не смогли отправить сообщение по какой-то причине, например,
		# у бота нет прав админа либо в группе выключена возможность отправлять сообщения.
		#
		# В таком случае, просто информируем пользователя что бот так работать не может,
		# и удаляемся.

		await bot.send_message(
			chat_id=event.from_user.id,
			text=(
				"<b>⚠️ Ошибка добавления бота в группу</b>.\n"
				"\n"
				f"По какой-то причине, Telehooper не смог заработать в группе «{event.chat.title}».\n"
				"Возможные на это причины:\n"
				" • У бота нет прав администратора в группе.\n"
				" • В группе отключена возможность отправлять сообщения.\n"
				"\n"
				"Пожалуйста, попробуйте выдать боту права администратора, а так же убедиться, что в группе включена возможность отправлять сообщения, и попробуйте снова.\n"
				"Telehooper автоматически покинет группу без Вашей помощи.\n"
				"\n"
				f"ℹ️ Возникают проблемы? Попросите помощи либо создайте баг-репорт (Github Issue), по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>."
			)
		)

		# Удаляем бота из группы.
		try:
			await bot.leave_chat(chat_id=event.chat.id)
		except:
			pass

		return

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

async def on_minibot_add(user: User) -> None:
	"""
	Вызывается при добавлении минибота в группу, в которой находится бот Telehooper.
	"""

	logger.debug(f"Событие добавление минибота {utils.get_telegram_logging_info(user)} в группу...")

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_other_member_add_handler(event: ChatMemberUpdated, bot: Bot) -> None:
	"""
	Handler для случая, если в группу (в котором находится Telehooper) был добавлен какой-то сторонний пользователь.
	"""

	if await _supergroup_convert_check(event.chat.id):
		return

	group = await get_group(event.chat)

	# В некоторых edge-case'ах группа может быть не найдена в БД.
	if not group:
		return

	# Проверяем, кого именно добавили в группу. Может быть несколько случаев:
	#  - 1. Добавили обычного пользователя. В таком случае стоит отобразить
	#       предупреждение о том, что добавлять "сторонних" юзеров не стоит.
	#  - 2. Добавили стороннего бота, который не является миниботом.
	#  - 3. Добавили минибота. В таком случае, событие об этом нужно сохранить в БД.
	#
	# Для начала, определяем, добавили ли минибота или нет.
	is_minibot = any([i for i in get_minibots().values() if i.id == event.new_chat_member.user.id])

	# Если пользователь добавил обычного пользователя или не минибота, то отображаем предупреждение:
	if not event.new_chat_member.user.is_bot or not is_minibot:
		if group["UserJoinedWarning"]:
			return

		text = (
			"<b>🫂 Группа-диалог</b>\n"
			"\n"
			"Вы добавили иного пользователя в данную группу!\n"
			"Это не запрещено ботом, однако так делать <b>не рекомендуется</b>, поскольку другой пользователь может читать Ваши сообщения, а так же бот может нестабильно работать в случаях присутствия «чужих» пользователей в группе.\n"
			"\n"
			f"ℹ️ Вы можете настроить бота так, что бы сообщения от других пользователей отправлялись от Вашего, либо от их собственного имени, либо что бы их сообщения полностью игнорировались. Зайдите в <a href=\"{utils.create_command_url('/s Services')}\">настройки сервисов</a> и найдите соответствующую настройку для изменения поведения в таких случаях."
		)

		if not is_minibot:
			minibots_str = "\n".join([f" • @{minibot}." for minibot in get_minibots().keys()])

			text = (
				"<b>🫂 Группа-диалог</b>\n"
				"\n"
				"Вы добавили стороннего бота в данную группу! Хотя это и не запрещено ботом, так делать <b>не рекомендуется</b>.\n"
				"Несмотря на то, что даже при повышении прав, <a href=\"https://core.telegram.org/bots/faq#why-doesn-39t-my-bot-see-messages-from-other-bots\">добавленный Вами бот не сможет читать сообщения от чужих ботов</a>, он может создавать неудобства при общении с собеседником из сервиса.\n"
				"\n"
				f"ℹ️ Вы пытались добавить «минибота»? Если да, то Вы добавили не того бота. Вот список миниботов, которых можно добавлять:\n"
				f"{minibots_str}"
			)

		await bot.send_message(chat_id=event.chat.id, text=text, disable_web_page_preview=True)

		# Сохраняем то, что мы предупредили пользователя.
		group["UserJoinedWarning"] = True
		await group.save()

		return

	# Пользователь добавил минибота. Нужно сохранить информацию об этом в БД.
	minibot_username = event.new_chat_member.user.username

	logger.debug(f"Добавление минибота @{minibot_username} в группу \"{event.chat.full_name}\"")

	# Что бы предотвратить флуд сообщения об успешном добавлении, нужно отправить сообщение об этом лишь раз.
	first_add = False
	if event.chat.id not in _minibot_adds:
		_minibot_adds[event.chat.id] = []

		first_add = True

	_minibot_adds[event.chat.id].append(minibot_username)

	# Если это не первое добавление, то ничего больше не делаем и не сохраняем.
	if not first_add:
		return

	await asyncio.sleep(1)

	await bot.send_message(
		chat_id=event.chat.id,
		text=(
			"<b>🫂 Группа-диалог</b>\n"
			"\n"
			f"Минибот @{minibot_username} {('(и ещё ' + str(len(_minibot_adds[event.chat.id]) - 1) + ' других) ') if len(_minibot_adds[event.chat.id]) > 1 else ''}был успешно подключён к данной группе! 🎉\n"
			"Если данная группа Telegram связана с беседой сервиса, то Telehooper автоматически определит то, с каким пользователем беседы должен быть связан данный минибот.\n"
			"\n"
			"Давать права администратора миниботам нет никакой необходимости.\n"
			"\n"
			"ℹ️ Вы можете просмотреть список добавленных миниботов и другую информацию о данной группе в команде /this."
		)
	)

	group["Minibots"].extend(i for i in _minibot_adds[event.chat.id] if i not in group["Minibots"])
	await group.save()

	del _minibot_adds[event.chat.id]

@router.callback_query(F.data == "/this showAdminTips", F.message.as_("msg"))
async def show_platform_admin_steps_inline_handler(query: CallbackQuery, msg: Message, bot: Bot) -> None:
	"""
	Handler, вызываемый, если пользователь в welcome-сообщении нажал на кнопку с инструкцией по выдаче прав администратора.
	"""

	await TelehooperAPI.edit_or_resend_message(
		bot,
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
			f" • Найдите бота @{utils.get_bot_username()}.\n"
			" • Разрешите всё, кроме пункта «Анонимность».\n"
			"\n"
			"Android:\n"
			" • Откройте список участников группы.\n"
			" • Зажмите палец над этим ботом.\n"
			" • Разрешите всё, кроме пункта «Анонимность».\n"
			"\n"
			"<i>⏳ Данное сообщение отредактируется после получения прав администратора в беседе...</i>"
		),
		message_to_edit=msg,
		chat_id=msg.chat.id,
		query=query
	)

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=(RESTRICTED | MEMBER | KICKED) >> (ADMINISTRATOR | CREATOR)))
async def on_user_promoted_handler(event: ChatMemberUpdated, bot: Bot):
	"""
	Handler, вызываемый, если пользователя повысили в группе.
	"""

	# Проверяем, что повысили именно бота.
	if event.new_chat_member.user.id != bot.id:
		return

	await asyncio.sleep(1)

	group = await get_group(event.chat)

	# В некоторых edge-case'ах группа может быть не найдена в БД.
	if not group:
		return

	# Пытаемся отредактировать сообщение.
	#
	# Если группа была конвертирована в супергруппу, то бот не сможет его отредактировать, поэтому мы его просто отправим.
	try:
		await group_convert_message(bot, event.chat.id, event.from_user, group["StatusMessageID"], called_from_command=False)
	except:
		await group_convert_message(bot, event.chat.id, event.from_user, None, called_from_command=False)

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=(ADMINISTRATOR | CREATOR) >> (RESTRICTED | MEMBER)))
async def on_user_demotion_handler(event: ChatMemberUpdated, bot: Bot):
	"""
	Handler, вызываемый, если пользователя в группе понизили.
	"""

	# Проверяем, что понизили именно бота.
	if event.new_chat_member.user.id != bot.id:
		return

	await asyncio.sleep(1)

	group = await get_group(event.chat)

	# В некоторых edge-case'ах группа может быть не найдена в БД.
	if not group:
		return

	# Проверяем, что у бота ранее были права администратора.
	if not group["AdminRights"]:
		return

	# Запоминаем, что у бота теперь нет прав админа.
	group["AdminRights"] = False
	await group.save()

	await bot.send_message(
		event.chat.id,
		(
			"<b>⚠️ Предупреждение о работе бота в этой группе</b>.\n"
			"\n"
			"Похоже, что Вы понизили бота Telehooper в этой группе. Бот продолжит работу, однако его стабильность может быть нарушена.\n"
			"\n"
			"Рекомендуется выдать боту права администратора, что бы он мог работать стабильно."
		)
	)

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def on_user_chat_kick_handler(event: ChatMemberUpdated, bot: Bot):
	"""
	Handler, вызываемый, если пользователя удалили из группы.
	"""

	# Проверяем, что понизили именно бота.
	# TODO: Если из группы вышел именно владелец, то написать ему в ЛС об этом, и предложить вернуться, в ином случае - удалить группу.
	if event.new_chat_member.user.id != bot.id:
		return

	await asyncio.sleep(1)

	# Если группа не была сохранена в БД, то значит что удалять нечего.
	if not get_group(event.chat):
		return

	# Удаляем группу из БД.
	await TelehooperAPI.delete_group_data(
		event.chat.id,
		fully_delete=True,
		bot=bot
	)

@router.message(F.migrate_to_chat_id)
async def group_to_supergroup_convert_handler(message: Message, bot: Bot):
	"""
	Handler для события конвертации Telegram-группы в супергруппу.

	При конвертации в супергруппу Telegram меняет ID группы.
	"""

	old_chat_id = message.chat.id
	new_chat_id = cast(int, message.migrate_to_chat_id)

	logger.debug(f"Telegram-группа с ID {old_chat_id} конвертировалась в supergroup'у с ID {new_chat_id}")

	new_chat = await bot.get_chat(new_chat_id)

	_supergroup_converts.append(old_chat_id)
	_supergroup_converts.append(new_chat_id)

	db = await get_db()

	# Пытаемся получить ассоциированного с данной группой пользователем.
	group_owner = None
	async for user in db.docs(prefix="user_"):
		if old_chat_id not in user["Groups"]:
			continue

		group_owner = user

	if not group_owner:
		logger.debug(f"Владелец группы, которая была конвертирована в супергруппу не был найден. Старый ID: {old_chat_id}, новый: {new_chat_id}")

	# Редактируем старую группу, и создаём новую с новым ID и прочими параметрами.
	group_old = await get_group(message.chat)
	if not group_old:
		return

	old_group_data = group_old._data.copy()

	del old_group_data["_id"]
	del old_group_data["_rev"]

	old_group_data["ID"] = new_chat_id
	old_group_data["LastActivityAt"] = utils.get_timestamp()

	# Создаём новый объект группы из БД.
	group_new = await db.create(f"group_{new_chat_id}", exists_ok=False, data=old_group_data)

	# Сохраняем новую группу.
	await group_new.save()

	# Удаляем старый объект группы из БД.
	await group_old.delete()

	# Редактируем информацию у владельца группы.
	if group_owner:
		group_owner["Groups"].remove(old_chat_id)
		group_owner["Groups"].append(new_chat_id)

		if "VK" in group_owner["Connections"]:
			for group in group_owner["Connections"]["VK"]["OwnedGroups"].values():
				if group["GroupID"] != old_chat_id:
					continue

				group["GroupID"] = new_chat_id

		# Сохраняем изменения у владельца группы.
		await group_owner.save()

	# Фиксим все subgroup'ы, что бы в них был новый ID.
	for subgroup in TelehooperAPI.get_all_subgroups():
		if subgroup.parent.chat.id != old_chat_id:
			continue

		subgroup.parent.chat = new_chat

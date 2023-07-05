# coding: utf-8

from typing import cast

from aiogram import F, Bot, Router, types
from aiogram.filters import Command, Text

from consts import CommandButtons
from DB import get_group, get_user
from services.vk.telegram_handlers.this import router as VKRouter


router = Router()
router.include_router(VKRouter)

async def group_convert_message(chat_id: int, user: types.User, message_to_edit: types.Message | int | None = None, called_from_command: bool = True) -> None:
	"""
	Сообщение у команды /this, либо же при выдаче прав администратора боту после его добавления в группу.
	"""

	bot = Bot.get_current()

	if not bot:
		return

	try:
		group = await get_group(chat_id)
	except:
		await bot.send_message(
			chat_id,
			text=(
				"<b>⚠️ Ошибка при создании группы-диалога</b>.\n"
				"\n"
				"Что-то пошло не так, и данная группа не была сохранена в базе данных бота.\n"
				"Пожалуйста, исключите бота Telehooper и снова добавьте его в группу, следуя последующим инструкциям.\n"
				"\n"
				"ℹ️ Если данная проблема повторяется, в таком случае создайте Github Issue у репозитория Telehooper, ссылку можно найти в команде <code>/faq 6</code>."
			)
		)

		return

	# Сохраняем то, что у бота есть права администратора в группе.
	group["AdminRights"] = True

	await group.save()

	db_user = await get_user(user)

	if not db_user["Connections"]:
		_text = (
			"<b>🫂 Группа-диалог</b>.\n"
			"\n"
			f"{'Вы пытаетесь' if called_from_command else 'Отлично! Права администратора были получены, однако в данный момент, Вы пытаетесь'} подключить группу к сервису, пока как у Вас нет никаких подключённых сервисов. 😔\n"
			"\n"
			f"ℹ️ Вы можете подключить сервис к Telehooper, воспользовавшись командой /connect. {'' if called_from_command else 'После подключения сервисов Вы сможете вернуться в этот диалог и попробовать снова, прописав команду /this.'}"
		)

		if message_to_edit:
			await bot.edit_message_text(
				text=_text,
				chat_id=chat_id,
				message_id=message_to_edit.message_id if isinstance(message_to_edit, types.Message) else message_to_edit
			)
		else:
			await bot.send_message(
				chat_id,
				text=_text
			)

		return

	keyboard = types.InlineKeyboardMarkup(
		inline_keyboard=[
			[
				# TODO: Убедиться, что сервис и вправду подключён.

				types.InlineKeyboardButton(text="ВКонтакте", callback_data="/this vk")
			]
		]
	)

	footer_txt = (
		"Вы пытаетесь подключить группу к сервису.\n"
		"После подключения группы к сервису Вы сможете получать сообщения или другой контент с нужного Вам сервиса.\n"
	) if called_from_command else (
		"Отлично! Вы выдали необходимые мне права администратора.\n"
		"Теперь Вы можете выбрать нужный сервис, а после указать, какой именно контент Вы хотите получать с сервиса.\n"
	)

	_text = (
		"<b>🫂 Группа-диалог</b>.\n"
		"\n"
		f"{footer_txt}"
		"\n"
		"В данный момент, к боту подключено следующее:\n"
		f" • <b>ВКонтакте</b>: <a href=\"vk.com/{db_user['Connections']['VK']['Username']}\">{db_user['Connections']['VK']['FullName']}</a>.\n"
		"\n"
		f"ℹ️ {'Выберите нужный сервис из списка ниже.' if called_from_command else 'Если Вы потеряете данное сообщение, то Вы сможете вызвать его снова, прописав команду <code>/this</code>.'}"
	)

	if message_to_edit:
		await bot.edit_message_text(
			text=_text,
			chat_id=chat_id,
			message_id=message_to_edit.message_id if isinstance(message_to_edit, types.Message) else message_to_edit,
			reply_markup=keyboard,
			disable_web_page_preview=True
		)
	else:
		await bot.send_message(
			chat_id,
			text=_text,
			reply_markup=keyboard,
			disable_web_page_preview=True
		)

@router.message(Command("this"))
@router.message(Text(CommandButtons.THIS))
async def this_command_handler(msg: types.Message):
	"""
	Handler для команды `/this`.
	"""

	# Проверка, что команда была вызвана в группе.
	if msg.chat.type == "private":
		await msg.reply(
			"<b>⚠️ Ошибка выполнения команды</b>.\n"
			"\n"
			"Данная команда может быть вызвана только в группе, к которой Вы хотите подключить сервис.\n"
		)

		return

	await group_convert_message(msg.chat.id, cast(types.User, msg.from_user), called_from_command=True)

@router.callback_query(Text("/this"), F.message.as_("msg"))
async def this_inline_handler(query: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии на нажатии на кнопку "назад", показывая содержимое команды `/this`.
	"""

	await group_convert_message(msg.chat.id, cast(types.User, query.from_user), message_to_edit=query.message, called_from_command=False)

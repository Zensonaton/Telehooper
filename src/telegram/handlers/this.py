# coding: utf-8

from typing import cast

from aiogram import Bot, F, Router
from aiogram.filters import Command, Text
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, User)

from api import TelehooperAPI, TelehooperGroup
from consts import CommandButtons
from services.vk.telegram_handlers.this import router as VKRouter


router = Router()
router.include_router(VKRouter)

async def group_convert_message(chat_id: int, user: User, message_to_edit: Message | int | None = None, called_from_command: bool = True) -> None:
	"""
	Сообщение у команды /this, либо же при выдаче прав администратора боту после его добавления в группу.
	"""

	bot = Bot.get_current()
	assert bot

	telehooper_user = await TelehooperAPI.get_user(user)

	try:
		telehooper_group = await TelehooperAPI.get_group(telehooper_user, chat_id)
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

	telehooper_group = cast(TelehooperGroup, telehooper_group)

	# Сохраняем то, что у бота есть права администратора в группе.
	telehooper_group.document["AdminRights"] = True

	await telehooper_group.document.save()

	# Проверяем на то, что данная группа уже является диалогом.
	if telehooper_group.chats:
		await TelehooperAPI.send_or_edit_message(
			text=(
				"<b>🫂 Группа-диалог</b>.\n"
				"\n"
				f"Данная группа уже является диалогом(-и). Настройка такого диалога будет добавлена в будущих обновлениях бота. 👀"
			),
			chat_id=chat_id,
			message_to_edit=message_to_edit
		)

		return

	# Проверяем на наличие подключённых сервисов.
	if not telehooper_user.document["Connections"]:
		await TelehooperAPI.send_or_edit_message(
			text=(
				"<b>🫂 Группа-диалог</b>.\n"
				"\n"
				f"{'Вы пытаетесь' if called_from_command else 'Отлично! Права администратора были получены, однако в данный момент, Вы пытаетесь'} подключить группу к сервису, пока как у Вас нет никаких подключённых сервисов. 😔\n"
				"\n"
				f"ℹ️ Вы можете подключить сервис к Telehooper, воспользовавшись командой /connect. {'' if called_from_command else 'После подключения сервисов Вы сможете вернуться в этот диалог и попробовать снова, прописав команду /this.'}"
			),
			chat_id=chat_id,
			message_to_edit=message_to_edit
		)

		return

	keyboard = InlineKeyboardMarkup(
		inline_keyboard=[
			[
				# TODO: Убедиться, что сервис и вправду подключён.

				InlineKeyboardButton(text="ВКонтакте", callback_data="/this vk")
			]
		]
	)

	await TelehooperAPI.send_or_edit_message(
		text=(
			"<b>🫂 Группа-диалог</b>.\n"
			"\n"
			f"{'Вы пытаетесь подключить группу к сервису.' if called_from_command else 'Отлично! Вы выдали необходимые мне права администратора.'}\n"
			f"{'После подключения группы к сервису Вы сможете получать сообщения или другой контент с нужного Вам сервиса.' if called_from_command else 'Теперь Вы можете выбрать нужный сервис, а после указать, какой именно контент Вы хотите получать с сервиса.'}\n"
			"\n"
			"В данный момент, к боту подключено следующее:\n"
			f" • <b>ВКонтакте</b>: <a href=\"vk.com/{telehooper_user.connections['VK']['Username']}\">{telehooper_user.connections['VK']['FullName']}</a>.\n"
			"\n"
			f"ℹ️ {'Выберите нужный сервис из списка ниже.' if called_from_command else 'Если Вы потеряете данное сообщение, то Вы сможете вызвать его снова, прописав команду <code>/this</code>.'}"
		),
		chat_id=chat_id,
		message_to_edit=message_to_edit,
		disable_web_page_preview=True,
		reply_markup=keyboard
	)

@router.message(Command("this"))
@router.message(Text(CommandButtons.THIS))
async def this_command_handler(msg: Message):
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

	await group_convert_message(msg.chat.id, cast(User, msg.from_user), called_from_command=True)

@router.callback_query(Text("/this"), F.message.as_("msg"), F.from_user.as_("user"))
async def this_inline_handler(query: CallbackQuery, msg: Message, user: User) -> None:
	"""
	Inline Callback Handler для команды `/this`.

	Вызывается при нажатии на нажатии на кнопку "назад", показывая содержимое команды `/this`.
	"""

	await group_convert_message(msg.chat.id, user, message_to_edit=query.message, called_from_command=False)

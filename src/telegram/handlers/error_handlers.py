# coding: utf-8

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery, Chat, ErrorEvent, Message
from loguru import logger

import utils
from api import TelehooperAPI


router = Router()

def exception_filter(event: ErrorEvent) -> bool:
	"""
	Фильтр для проверки на 'полезность' исключения. Если это исключения типа "Message Not Modified" или подобное, то данный метод возвращает `False`, в ином случае возвращает `True`.
	"""

	return utils.is_useful_exception(event.exception)

async def handle_error(event: ErrorEvent, bot: Bot, chat: Chat) -> bool:
	"""
	Ранний обработчик ошибок. Если вернул значение True, то значит, что обработчик сработал и дальнейшая обработка не требуется.

	:param event: Событие ошибки.
	:param bot: Экземпляр бота.
	:param chat: Чат, в котором произошла ошибка.
	"""

	exc = event.exception
	if isinstance(exc, TelegramForbiddenError) and "bot was kicked" in exc.message:
		logger.debug("Пользователь удалил бота из группы.")

		await TelehooperAPI.delete_group_data(chat, fully_delete=True)

	return False

@router.errors(F.update.message.as_("msg"), exception_filter)
async def message_error_handler(event: ErrorEvent, msg: Message, bot: Bot) -> None:
	"""
	Error Handler для случаев с сообщениями.
	"""

	if await handle_error(event, bot, msg.chat):
		return

	logger.exception(f"Ошибка при обработке сообщения от пользователя {utils.get_telegram_logging_info(msg.from_user)}:", event.exception)

	await msg.answer(
		"<b>⚠️ У бота произошла ошибка</b>.\n"
		"\n"
		"<i><b>Упс!</b></i> Что-то пошло не так, и бот столкнулся с ошибкой. 😓\n"
		"\n"
		"<b>Текст ошибки, если Вас попросили его отправить</b>:\n"
		f"<code>{event.exception.__class__.__name__}: {event.exception}</code>.\n"
		"\n"
		f"ℹ️ Пожалуйста, подождите, перед тем как попробовать снова. Если проблема не проходит через время - попробуйте попросить помощи либо создать баг-репорт (Github Issue), по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>."
	)

@router.errors(F.update.callback_query.as_("query"), exception_filter)
async def callback_query_error_handler(event: ErrorEvent, query: CallbackQuery, bot: Bot) -> None:
	"""
	Error Handler для случаев с Inline Callback Query.
	"""

	if query.message and await handle_error(event, bot, query.message.chat):
		return

	logger.exception(f"Ошибка при обработке callback query от пользователя {utils.get_telegram_logging_info(query.from_user)}:", event.exception)

	await query.answer(
		"⚠️ Ошибка\n"
		"\n"
		"У бота произошла ошибка:\n"
		f"{event.exception.__class__.__name__}: {event.exception}\n"
		"\n"
		"Попробуйте позже.", show_alert=True
	)

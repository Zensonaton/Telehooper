# coding: utf-8

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, ErrorEvent, Message
from loguru import logger

import utils


def exception_filter(event: ErrorEvent) -> bool:
	"""
	Фильтр для проверки на 'полезность' исключения. Если это исключения типа "Message Not Modified" или подобное, то данный метод возвращает `False`, в ином случае возвращает `True`.
	"""

	return utils.is_useful_exception(event.exception)

router = Router()

@router.errors(F.update.message.as_("msg"), exception_filter)
async def message_error_handler(event: ErrorEvent, msg: Message) -> None:
	"""
	Error Handler для случаев с сообщениями.
	"""

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
async def callback_query_error_handler(event: ErrorEvent, query: CallbackQuery) -> None:
	"""
	Error Handler для случаев с Inline Callback Query.
	"""

	logger.exception(f"Ошибка при обработке callback query от пользователя {utils.get_telegram_logging_info(query.from_user)}:", event.exception)

	await query.answer(
		"⚠️ Ошибка\n"
		"\n"
		"У бота произошла ошибка:\n"
		f"{event.exception.__class__.__name__}: {event.exception}\n"
		"\n"
		"Попробуйте позже.", show_alert=True
	)

# coding: utf-8

from aiogram import F, Router
from aiogram.types import CallbackQuery, ErrorEvent, Message
from loguru import logger

import utils


router = Router()

@router.errors(F.update.message.as_("msg"))
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
		"ℹ️ Попробуйте ещё раз через некоторое время. Если ошибка повторится, то обратитесь к разработчику бота: <code>/faq 6</code>."
	)

@router.errors(F.update.callback_query.as_("query"))
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

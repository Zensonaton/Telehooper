# coding: utf-8

import asyncio

from aiogram import F
from aiogram import Router as RouterT
from aiogram import types
from aiogram.filters import Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from pydantic import SecretStr
import utils

from . import utils as vk_utils
from .consts import VK_OAUTH_URL


Router = RouterT()

@Router.callback_query(Text("connect vk"), F.message.as_("message"))
async def connect_vk_handler(query: types.CallbackQuery, message: types.Message) -> None:
	"""
	Inline Handler для команды /connect: Вызывается, когда пользователь нажал на кнопку "ВКонтакте".
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[
			InlineKeyboardButton(text="🔙 Назад", callback_data="connect"),
			InlineKeyboardButton(text="🔗 Авторизоваться", url=VK_OAUTH_URL)
		]
	])

	await message.edit_text(
		"<b>🌐 Подключение сервиса — ВКонтакте</b>.\n"
		"\n"
		"Для подключения ВКонтакте нужно сделать следующее:\n"
		f"1. Авторизуйтесь на сайте: <a href=\"{VK_OAUTH_URL}\">🔗 перейти</a>.\n"
		"2. Разрешите приложению «Kate Mobile»* войти в Ваш аккаунт ВКонтакте.\n"
		"3. Скопируйте текст с адресной строки сюда. Страница, с которой нужно скопировать адресную строку, имеет следующий текст:\n"
		"  <i>Пожалуйста, не копируйте данные из адресной строки для сторонних сайтов.</i>\n"
		"4. Отправьте содержимое адресной строки в этот же чат. Она выглядит примерно так:\n"
		"<code>https://oauth.vk.com/blank.html#access_token=vk1.a.0xBADD...CAFEexpires_in=0&user_id=123456</code>\n"
		"\n"
		"ℹ️ Из-за технических <a href=\"https://dev.vk.com/reference/roadmap#Ограничение Messages API\">ограничений API ВКонтакте</a>, авторизация производится через приложение «Kate Mobile». Подробнее про это написано <a href=\"https://github.com/Zensonaton/Telehooper/blob/rewrite/src/services/vk/README.md#ограничения-messaging-api\">здесь</a>.",
		disable_web_page_preview=True,
		reply_markup=keyboard
	)

@Router.message(Text(startswith="https://oauth.vk.com/authorize"))
async def connect_vk_wrong_url(msg: types.Message) -> None:
	"""
	Handler для команды /connect: Вызывается, если пользователь отправил не ту ссылку на авторизацию ВКонтакте.
	"""

	await msg.answer(
		"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
		"\n"
		"Упс, похоже, что Вы по-ошибке отправили не ту ссылку. 👀\n"
		"\n"
		f"Перейдя <a href=\"{VK_OAUTH_URL}\">на страницу с авторизацией</a>, Вам необходимо нажать на кнопку «Разрешить», и ссылку с адресной строки браузера отправить сюда. Ссылка, которую нужно отправить мне имеет следующий вид:\n"
		"<code>https://oauth.vk.com/blank.html#access_token=vk1.a.0xBADD...CAFEexpires_in=0&user_id=123456</code>\n"
		"\n"
		"ℹ️ Если у Вас возникли проблемы, то постарайтесь снова прочитать содержимое информации у команды /connect.",
	)

@Router.message(Text(startswith="https://oauth.vk.com/blank.html#access_token="))
async def connect_vk_token_handler(msg: types.Message) -> None:
	"""
	Handler для команды /connect: Вызывается, когда пользователь отправил токен ВКонтакте.
	"""

	token = vk_utils.extract_access_token_from_url(msg.text or "")
	if not token or len(token) != 220 or not token.startswith("vk1.a."):
		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			"Похоже, что Вы отправили неполную ссылку, либо же произошли изменения на стороне ВКонтакте. Попробуйте ещё раз.\n"
			"\n"
			"ℹ️ Если Вы уверены, что делаете всё правильно, то создайте Github Issue у репозитория Telehooper, ссылку можно найти в команде /faq.",
		)

		return

	token = SecretStr(token)

	# Всё в порядке.
	try:
		await msg.delete()
	except:
		pass

	await msg.answer(
		"<b>🌐 Подключение сервиса — ВКонтакте</b>.\n"
		"\n"
		"Отлично, я получил все данные необходимые для авторизации во ВКонтакте. Твоё предущее сообщение было удалено специально, в целях безопасности. 👀\n"
		"\n"
		"<i>⏳ Мне нужно проверить что всё работает корректно, ожидайте...</i>",
		disable_web_page_preview=True
	)

	# Пытаемся авторизоваться.
	try:
		auth_result = await auth_token(token)
	except Exception as error:
		logger.exception(f"Ошибка при авторизации у пользователя Telegram {utils.get_telegram_logging_info(msg.from_user)}: {error}")

		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			"К сожалению, произошла ошибка при попытке авторизоваться во ВКонтакте. Попробуйте ещё раз позже.\n"
			"\n"
			"ℹ️ Если данная проблема повторяется, в таком случае создайте Github Issue у репозитория Telehooper, ссылку можно найти в команде /faq.",
		)

		return
	else:
		# TODO: Аватарка страницы, если она есть.

		await msg.answer(
			"<b>✅ Подключение ВКонтакте — успех</b>.\n"
			"\n"
			"Успешно! Я сумел подключиться к Вашему аккаунту ВКонтакте!\n"
			f"Я рад с Вами познакомиться, <b>{auth_result}</b>! 🙃\n"
			"\n"
			"ℹ️ Не знаете что делать дальше? В таком случае, воспользуйтесь командой <code>/help 5</code>.",
		)

async def auth_token(token: SecretStr) -> str:
	"""
	Пытается авторизоваться через токен ВКонтакте. Данный метод отправляет сообщения в чат "Избранное" во ВКонтакте, а так же в ЛС к специальному боту, для оповещения (что бы пользователь получил уведомление).

	Возвращает имя и фамилию пользователя.
	"""

	# Получаем информацию о пользователе.
	# TODO.

	# Отправляем сообщение в диалог «Избранное».
	# TODO.

	# Отправляем сообщение в ЛС к специальному боту, если это разрешено.
	# TODO.

	await asyncio.sleep(1.5)

	return "Имя Фамилия"

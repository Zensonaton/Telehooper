# coding: utf-8

"""Обработчик для команды `Self`."""

from aiogram import Bot, Dispatcher
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from aiogram.types import Message as MessageType
from Consts import VK_OAUTH_URL
from Consts import CommandThrottleNames as CThrottle
from Consts import InlineButtonCallbacks as CButtons
from Exceptions import CommandAllowedOnlyInPrivateChats
from TelegramBot import Telehooper
from loguru import logger

TelehooperBot: 	Telehooper 	= None # type: ignore
TGBot: 			Bot 		= None # type: ignore
DP: 			Dispatcher 	= None # type: ignore


def _setupCHandler(bot: Telehooper) -> None:
	"""
	Инициализирует команду `Self`.
	"""

	global TelehooperBot, TGBot, DP

	TelehooperBot = bot
	TGBot = TelehooperBot.TGBot
	DP = TelehooperBot.DP

	DP.register_message_handler(Me, commands=["me", "self", "myself", "profile", "service", "services"])
	DP.register_callback_query_handler(MeCallbackHandler, lambda query: query.data in [CButtons.CommandActions.DISCONNECT_SERVICE, CButtons.CommandMenus.VK_LOGIN_VKID, CButtons.CommandMenus.VK_LOGIN_PASSWORD, CButtons.CommandCallers.ME])


async def Me(msg: MessageType):
	# Убеждаемся, что команду отправили в приватном чате:
	if msg.chat.type != "private":
		raise CommandAllowedOnlyInPrivateChats

	await DP.throttle(CThrottle.SERVICES_LIST, rate=2, user_id=msg.from_user.id)

	await MeMessage(msg)

async def MeMessage(msg: MessageType, edit_message_instead: bool = False, user_id: int | None = None):
	# Получаем объект пользователя:
	user = await TelehooperBot.getBotUser(user_id or msg.from_user.id)

	# Если же у нас не подключён ВК, то показываем сообщения об этом:
	if not user.isVKConnected:
		_text = "<b>В данный момент у тебя ничего не подключено ⛔️\n\n</b>Подключить меня на данный момент можно только к <b>«ВКонтакте»</b>, однако, в будущем будет больше сервисов для подключения, к примеру, в будущем планируется поддержка <b>Whatsapp</b>. Внимательно следи за прогрессом в <a href=\"https://github.com/Zensonaton/Telehooper\">Github-репозитории проекта</a>. 👀\n\n🔗 Подключить аккаунт <b>ВКонтакте</b> к боту можно двумя методами, выбрать можно удобный:\n    <b>•</b> 🆔 <u>VK ID</u>: <b>Рекомендуемый метод.</b> Бот отправит тебе ссылку на авторизацию на официальном сайте ВКонтакте, и после авторизации тебе будет необходимо скопировать с адресной строки ссылку и отправить её мне. Рекомендуется, т. к. сайт - официален, и в случае взлома бота взломщики не смогут узнать твой логин и пароль.\n    <b>•</b> 🔐 <u>Пароль</u>: Тебе будет необходимо использовать специальную команду, в которой тебе придётся прописать логин и пароль от страницы ВКонтакте. Этот метод не рекомендуется, поскольку в случае взлома у злоумышленников может быть твой логин и пароль, а так же этот метод не будет работать, если на странице включена двухэтапная аутентификация.\n\n⚠️ Учти, что создатель бота не будет нести никакой ответственности в случае взлома бота. Если ты хочешь запустить бота локально, то помни, что все инструкции есть в <a href=\"https://github.com/Zensonaton/Telehooper\">Github-репозитории</a>.\n\n\n⚙️ Выбери понравившийся тебе метод авторизации в аккаунт <b>ВКонтакте</b> для получения дополнительной информации:"
		keyboard = InlineKeyboardMarkup().add(
			InlineKeyboardButton("🆔 VK ID", callback_data=CButtons.CommandMenus.VK_LOGIN_VKID),
			InlineKeyboardButton("🔐 Пароль", callback_data=CButtons.CommandMenus.VK_LOGIN_PASSWORD),
		)

		if edit_message_instead:
			await msg.edit_text(_text, reply_markup=keyboard)
		else:
			await msg.answer(_text, reply_markup=keyboard)
		return

	# У нас подключён ВК, показываем сообщение с управлением подключённой страницы:
	keyboard = InlineKeyboardMarkup().add(
		InlineKeyboardButton("🛑 Отключить сервис", callback_data=CButtons.CommandActions.DISCONNECT_SERVICE),
	)
	_text = "<b>Подключённые сервисы 🔗\n\n</b>В данный момент, к боту подключён лишь один сервис, <b>«ВКонтакте»</b>.\n\n⚙️ Выбери операцию над сервисом <b>ВКонтакте</b>:"
	if edit_message_instead:
		await msg.edit_text(_text, reply_markup=keyboard)
	else:
		await msg.answer(_text, reply_markup=keyboard)

async def MeCallbackHandler(query: CallbackQuery):
	# Получаем объект пользователя:
	user = await TelehooperBot.getBotUser(query.from_user.id)

	if query.data == CButtons.CommandActions.DISCONNECT_SERVICE:
		if not user.isVKConnected:
			await query.answer("Что-то пошло не так.")
		else:
			# await user.vkMAPI.disconnectService(AccountDisconnectType.INITIATED_BY_USER, True)
			pass
	elif query.data == CButtons.CommandCallers.ME:
		await MeMessage(query.message, True, query.from_user.id)
	elif query.data == CButtons.CommandMenus.VK_LOGIN_VKID:
		keyboard = InlineKeyboardMarkup().add(
			InlineKeyboardButton("🔑 Авторизоваться", url=VK_OAUTH_URL)
		).add(
			InlineKeyboardButton("🔙 Назад", callback_data=CButtons.CommandCallers.ME)
		)

		await query.message.edit_text("<b>Авторизация через 🆔 VK ID\n\n</b>Что бы авторизоваться в боте, тебе необходимо пройти авторизацию на официальном сайте <b>ВКонтакте</b>. Из-за технических <a href=\"https://dev.vk.com/reference/roadmap#2019%20|%20%D0%A4%D0%B5%D0%B2%D1%80%D0%B0%D0%BB%D1%8C\">ограничений API ВКонтакте</a>, авторизация производится через приложение «Kate Mobile», это нормально, и волноваться по этому поводу не стоит. После нажатия на кнопку «Разрешить», ты попадёшь на страницу где говорится <i>«Пожалуйста, не копируйте данные из адресной строки, ...»</i>, и как бы страница не говорила, для авторизации придётся скопировать всю ссылку и отправить мне.\nПожалуйста, не забывай, что бот <b>полностью прозрачен</b>, и весь его код можно просмотреть на <a href=\"https://github.com/Zensonaton/Telehooper\">Github проекта</a>.\n\n«Готовая» ссылка выглядит примерно так: <code>https://oauth.vk.com/blank.html#access_token=0xBADD...CAFEexpires_in=0&user_id=123456\n\n\n</code>⚙️ Проведи процедуру авторизации на официальном сайте <b>ВКонтакте</b>:", reply_markup=keyboard)
	elif query.data == CButtons.CommandMenus.VK_LOGIN_PASSWORD:
		keyboard = InlineKeyboardMarkup().add(
			InlineKeyboardButton("🔙 Назад", callback_data=CButtons.CommandCallers.ME)
		)

		await query.message.edit_text("<b>Авторизация через 🔐 пароль\n\n</b>Перед тем как авторизоваться в боте используя метод логина и пароля, ты должен учесть следующее:\n    <b>•</b> Этот метод менее безопасен, поскольку в случае взлома бота, у взломщиков будет информация о твоём <b>логине и пароле</b>.\n    <b>•</b> Этот метод авторизации не будет работать, если к твоей странице подключена двухэтапная аутентификация.\n\nПрочитав информацию выше, ты можешь начать авторизацию воспользовавшись командою <code>/vklogin логин пароль</code>. Пример использования команды: <code>/vklogin paveldurovv tgisbetter</code>. Если тебе не нравится этот метод авторизации, то нажми на кнопку <b>«Назад»</b>, расположенную ниже.\nПожалуйста, не забывай, что бот <b>полностью прозрачен</b>, и весь его код можно просмотреть на <a href=\"https://github.com/Zensonaton/Telehooper\">Github проекта</a>.\n\n\n⚙️ Воспользуйся командой <code>/vklogin</code> что бы авторизоваться в боте:", reply_markup=keyboard)

	await query.answer()

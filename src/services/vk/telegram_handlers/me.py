# coding: utf-8

from aiogram import Bot, F, Router
from aiogram.filters import Text
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, User)
from loguru import logger
from pydantic import SecretStr

import utils
from api import TelehooperAPI
from services.service_api_base import ServiceDisconnectReason
from services.vk import utils as vk_utils
from services.vk.consts import (VK_INVISIBLE_CHARACTER,
                                VK_MESSAGES_API_RESTRICTION_DOCS_GITHUB_URL,
                                VK_MESSAGES_API_RESTRICTION_DOCS_VK_URL,
                                VK_OAUTH_URL)
from services.vk.exceptions import AccountDeactivatedException
from services.vk.service import VKServiceAPI
from services.vk.vk_api.api import VKAPI
from config import config


router = Router()

@router.callback_query(Text("/me vk"), F.message.as_("msg"), F.from_user.as_("user"))
async def me_vk_inline_handler(query: CallbackQuery, msg: Message, user: User) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Открывает меню с управлением сервиса ВКонтакте.
	Вызывается при нажатии пользователем кнопки "ВКонтакте" в команде `/me`.
	"""

	telehooper_user = await TelehooperAPI.get_user(user)
	use_mobile_vk = await telehooper_user.get_setting("Services.VK.MobileVKURLs")

	if telehooper_user.get_vk_connection():
		# У пользователя есть страница ВКонтакте.

		id = telehooper_user.connections["VK"]["ID"]
		full_name = telehooper_user.connections["VK"]["FullName"]
		domain = telehooper_user.connections["VK"]["Username"]

		dialogues = []
		for dialogue in telehooper_user.connections["VK"]["OwnedGroups"].values():
			chat = "чат"

			chat_url = None
			if dialogue["GroupID"] < -1e12:
				chat_url = f"https://t.me/c/{-int(dialogue['GroupID'] + 1e12)}"
			elif dialogue["URL"]:
				chat_url = f"https://t.me/{utils.decrypt_with_env_key(dialogue['URL'])}"

			if chat_url:
				chat = f"<a href=\"{chat_url}\">чат</a>"

			dialogues.append(f" • <a href=\"{vk_utils.create_dialogue_link(dialogue['ID'], use_mobile_vk)}\">{dialogue['Name']}</a>: {chat}.")

		dialogues_str = "\n".join(dialogues)

		await TelehooperAPI.edit_or_resend_message(
			(
				"<b>👤 Профиль — ВКонтакте</b>.\n"
				"\n"
				"Вы управляете этой страницей ВКонтакте:\n"
				f" • <b>Страница</b>: {full_name} (<a href=\"{'m.' if use_mobile_vk else ''}vk.com/{domain}\">@{domain}</a>, ID {id}).\n"
				"\n"
				f"Диалогов и групп ВКонтакте в боте — {len(dialogues)} штук{'(-и):' if dialogues else '.'}\n"
				f"{dialogues_str if dialogues else ''}\n"
			),
			message_to_edit=msg,
			chat_id=msg.chat.id,
			disable_web_page_preview=True,
			reply_markup=InlineKeyboardMarkup(inline_keyboard=
				[
					[InlineKeyboardButton(text="🔙 Назад", callback_data="/me")],
					[
						InlineKeyboardButton(text="⛔️ Отключить от бота", callback_data="/me vk disconnect"),
					]
				]
			),
			query=query
		)

		return

	# У пользователя нет подключённой страницы ВКонтакте.
	await TelehooperAPI.edit_or_resend_message(
		(
			"<b>🌐 Подключение сервиса — ВКонтакте</b>.\n"
			"\n"
			"Шаги для подключения ВКонтакте:\n"
			f" • Авторизуйтесь на сайте: <a href=\"{VK_OAUTH_URL}\">🔗 перейти</a>.\n"
			" • Разрешите приложению «Kate Mobile»* войти в Ваш аккаунт ВКонтакте.\n"
			" • Скопируйте текст с адресной строки браузера сюда. Страница, с которой нужно скопировать адресную строку, имеет следующий текст:\n"
			"    <i>Пожалуйста, не копируйте данные из адресной строки для сторонних сайтов.</i>\n"
			" • Отправьте содержимое адресной строки в этот же чат. Она выглядит примерно так:\n"
			"<code>https://oauth.vk.com/blank.html#access_token=vk1.a...&user_id=123456</code>\n"
			"\n"
			f"ℹ️ Из-за технических <a href=\"{VK_MESSAGES_API_RESTRICTION_DOCS_VK_URL}\">ограничений API ВКонтакте</a>, авторизация производится через приложение «Kate Mobile». Подробнее про это написано <a href=\"{VK_MESSAGES_API_RESTRICTION_DOCS_GITHUB_URL}\">здесь</a>."
		),
		message_to_edit=msg,
		chat_id=msg.chat.id,
		disable_web_page_preview=True,
		reply_markup=InlineKeyboardMarkup(inline_keyboard=[
			[
				InlineKeyboardButton(text="🔙 Назад", callback_data="/me"),
				InlineKeyboardButton(text="🔗 Авторизоваться", url=VK_OAUTH_URL)
			]
		]),
		query=query
	)

@router.message(Text(startswith="https://oauth.vk.com/blank.html#access_token="), F.from_user.as_("user"))
async def connect_vk_token_handler(msg: Message, user: User, bot: Bot) -> None:
	"""
	Handler для команды `/connect`.

	Вызывается, когда пользователь отправил токен ВКонтакте.
	"""

	token = vk_utils.extract_access_token_from_url(msg.text or "")
	if not token or len(token) != 220 or not token.startswith("vk1.a."):
		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			"Похоже, что Вы отправили неполную ссылку, либо же произошли изменения на стороне ВКонтакте. Попробуйте ещё раз.\n"
			"\n"
			f"ℹ️ Вы считаете, что это ошибка? Вы уверены, что делаете всё правильно? Попробуйте попросить помощи либо создать баг-репорт (Github Issue), по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>."
		)

		return

	telehooper_user = await TelehooperAPI.get_user(user)

	await telehooper_user.restrict_in_debug()

	allow_tokens_storing = await telehooper_user.get_setting("Security.StoreTokens")
	use_mobile_vk = await telehooper_user.get_setting("Services.VK.MobileVKURLs")

	if telehooper_user.document["Connections"].get("VK"):
		# TODO: Автоматически отключать предыдущий аккаунт ВКонтакте, если он был подключён.
		# Либо же дать такую опцию пользователю.

		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			f"К Telehooper уже <a href=\"{'m.' if use_mobile_vk else ''}vk.com/id{telehooper_user.document['Connections']['VK']['ID']}\">подключён аккаунт ВКонтакте</a>. Вы не можете подключить сразу несколько аккаунтов одного типа к Telehooper.\n"
			"\n"
			"ℹ️ Для подключения нового аккаунта Вы можете можете отключить старый, для этого пропишите команду /me.",
			disable_web_page_preview=True
		)

		return

	# Всё в порядке.
	token = SecretStr(token)

	try:
		await msg.delete()
	except:
		pass

	await msg.answer(
		"<b>🌐 Подключение сервиса — ВКонтакте</b>.\n"
		"\n"
		"Отлично, я получил все данные необходимые для авторизации во ВКонтакте. Ваше предыдущее сообщение было удалено специально, в целях безопасности. 👀\n"
		"\n"
		"<i>⏳ Мне нужно проверить что всё работает корректно, ожидайте...</i>",
		disable_web_page_preview=True
	)

	# Пытаемся авторизоваться.
	try:
		auth_result = await authorize_by_token(user, token)

		# Сохраняем в базу данных сессию пользователя.
		telehooper_user.document["Connections"]["VK"] = {
			"Token": utils.encrypt_with_env_key(token.get_secret_value()) if allow_tokens_storing else None,
			"ConnectedAt": utils.get_timestamp(),
			"LastActivityAt": utils.get_timestamp(),
			"ID": auth_result["id"],
			"FullName": f"{auth_result['first_name']} {auth_result['last_name']}",
			"Username": auth_result["domain"],
			"OwnedGroups": {}
		}

		await telehooper_user.document.save()
	except AccountDeactivatedException as error:
		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			"К сожалению, Ваша страница ВКонтакте является удалённой, замороженной или заблокированной, либо же у аккаунта ВКонтакте не подтверждён номер телефона.\n"
			"\n"
			f"ℹ️ Бот ошибся? Ваша страница является «работающей»? Попросите помощи либо создайте баг-репорт (Github Issue), по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>."
		)
	except Exception as error:
		logger.exception(f"Ошибка при авторизации у пользователя Telegram {utils.get_telegram_logging_info(msg.from_user)}:", error)

		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			"К сожалению, произошла ошибка при попытке авторизоваться во ВКонтакте. Попробуйте ещё раз позже.\n"
			"\n"
			f"ℹ️ Пожалуйста, подождите, перед тем как попробовать снова. Если проблема не проходит через время - попробуйте попросить помощи либо создать баг-репорт (Github Issue), по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>."
		)
	else:
		_text = (
			"<b>✅ Подключение ВКонтакте — успех</b>.\n"
			"\n"
			"Успешно! Я сумел подключиться к Вашему аккаунту ВКонтакте!\n"
			f"Я рад с Вами познакомиться, <b>{auth_result['first_name']} {auth_result['last_name']}</b>! 🙃\n"
			"\n"
			f"ℹ️ Не понимаете что нужно делать дальше? Создайте группу в Telegram и добавьте туда этого бота, после чего следуйте инструкциям. Для более подробной информации обратитесь к команде <a href=\"{utils.create_command_url('/h 5')}\">/help</a>."
		)
		keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
			text="➕ Добавить в группу",
			url=f"https://t.me/{utils.get_bot_username()}?startgroup=1"
		)]])

		if not allow_tokens_storing:
			_text += (
				"\n"
				"⚠️ Предупреждение: Вы запретили боту сохранять токены авторизации в базу данных при помощи настройки {{Security.StoreTokens}}.\n"
				"Это значит, что после перезагрузки бота (которая может произойти в любой момент) Telehooper не сумеет восстановить соединение с Вашей страницей ВКонтакте.\n"
				"Если Вам такое поведение не нравится, то Вам нужно разрешить боту сохранять токены в БД, поставив значение «включено» у настройки {{Security.StoreTokens}}."
			)

		# Если у пользователя установлена фотография, то отправляем её вместе с сообщением.
		# В ином случае отправляем только текст.
		if auth_result["has_photo"]:
			await msg.answer_photo(
				photo=auth_result["photo_max"],
				caption=utils.replace_placeholders(_text),
				reply_markup=keyboard
			)
		else:
			await msg.answer(
				utils.replace_placeholders(_text),
				reply_markup=keyboard
			)

		# Создаём объект сервиса, а так же сохраняем его в память пользователя Telehooper.
		vkServiceAPI = VKServiceAPI(
			token=token,
			vk_user_id=auth_result["id"],
			user=telehooper_user
		)
		telehooper_user.save_connection(vkServiceAPI)

		await vkServiceAPI.start_listening(bot)

@router.message(Text(startswith="https://oauth.vk.com/authorize"))
async def connect_vk_wrong_url_handler(msg: Message) -> None:
	"""
	Handler для команды `/connect`.

	Вызывается, если пользователь отправил ссылку, которая не имеет токен ВКонтакте.
	"""

	await msg.answer(
		"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
		"\n"
		"Упс, похоже, что Вы по-ошибке отправили не ту ссылку. 👀\n"
		"\n"
		f"Перейдя <a href=\"{VK_OAUTH_URL}\">на страницу с авторизацией</a>, Вам необходимо нажать на кнопку «Разрешить», и ссылку с адресной строки браузера отправить сюда. Ссылка, которую нужно отправить мне имеет следующий вид:\n"
		"<code>https://oauth.vk.com/blank.html#access_token=vk1.a.0xBADD...CAFEexpires_in=0&user_id=123456</code>\n"
		"\n"
		"ℹ️ Не понимаете, как продолжить? Попробуйте снова последовать шагам из команды /connect, или же попросите помощи по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>.",
	)

async def authorize_by_token(user: User, token: SecretStr) -> dict:
	"""
	Пытается авторизоваться через токен ВКонтакте. Данный метод отправляет сообщения в чат "Избранное" во ВКонтакте, а так же в ЛС к специальному боту, для оповещения (что бы пользователь получил уведомление).

	Возвращает имя и фамилию пользователя.
	"""

	vk_api = VKAPI(token)

	# Получаем информацию о пользователе.
	user_info = await vk_api.get_self_info()

	if "deactivated" in user_info:
		raise AccountDeactivatedException(user_info["deactivated"])

	user_id = user_info["id"]

	# Отправляем сообщение в ЛС к специальному боту, если это разрешено.
	if config.vkbot_notifier_id:
		try:
			await vk_api.messages_send(
				peer_id=-abs(config.vkbot_notifier_id),
				message=(
					"Хей! Данное сообщение было отправлено Telegram-ботом «Telehooper». 😌\n"
					"\n"
					"Прочитай последующее сообщение в этом же чате для подробной информации, либо же перейди в диалог «Избранное».\n"
					"\n"
					"(код: telehooperSuccessAuth)"
				)
			)
		except AccountDeactivatedException as error:
			# Ничего не делаем. Данная ошибка обрабатывается в другом месте.

			raise error
		except Exception as error:
			logger.exception(f"Ошибка при отправке сообщения в ЛС к боту Telehooper (id {config.vkbot_notifier_id}): {error}")


	dot_symbol_space = f"{VK_INVISIBLE_CHARACTER}•{VK_INVISIBLE_CHARACTER}"

	# Отправляем сообщение в диалог "Избранное".
	await vk_api.messages_send(
		peer_id=user_id,
		message=(
			f"⚠️ ВАЖНАЯ ИНФОРМАЦИЯ ⚠️ {VK_INVISIBLE_CHARACTER * 15}\n"
			"\n"
			"Привет! 🙋\n"
			"Если Вы видите это сообщение, то это значит, что Telegram-бот под названием «Telehooper» был успешно подключён к Вашей странице ВКонтакте. Тот, кто подключился к Вашей странице сможет:\n"
			f"{dot_symbol_space}Читать все получаемые и отправляемые сообщения.\n"
			f"{dot_symbol_space}Отправлять сообщения.\n"
			f"{dot_symbol_space}Смотреть список диалогов.\n"
			"\n"
			"Telegram-пользователь, который подключил бота к Вашей странице:\n"
			f"{dot_symbol_space}{utils.get_telegram_logging_info(user, use_url=True)}.\n"
			"\n"
			"⚠ Если это были не Вы, то срочно в настройках подключённых приложений (https://vk.com/settings?act=apps) отключите приложение «Kate Mobile», после чего срочно поменяйте пароль от своей страницы ВКонтакте, поскольку произошедшее значит, что кто-то сумел войти в Ваш аккаунт ВКонтакте!\n"
		)
	)

	return user_info

@router.callback_query(Text("/me vk disconnect"), F.message.as_("msg"), F.from_user.as_("user"))
async def me_vk_disconnect_inline_handler(query: CallbackQuery, msg: Message, user: User) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Вызывается при нажатии на кнопку "Отключить от бота" в меню управления ВКонтакте.
	"""

	telehooper_user = await TelehooperAPI.get_user(user)

	await TelehooperAPI.edit_or_resend_message(
		"<b>⛔️ Отключение ВКонтакте</b>.\n"
		"\n"
		f"Вы уверены, что хотите отключить страницу «{telehooper_user.connections['VK']['FullName']}» от Telehooper?\n"
		"\n"
		"⚠️ Отключив страницу, Telehooper перестанет получать сообщения от ВКонтакте. Все подключённые диалоги будут отключены от бота.\n",
		message_to_edit=msg,
		chat_id=msg.chat.id,
		reply_markup=InlineKeyboardMarkup(inline_keyboard=
			[
				[InlineKeyboardButton(text="🔙 Назад", callback_data="/me vk"), InlineKeyboardButton(text="🔝 В начало", callback_data="/me")],
				[InlineKeyboardButton(text="⛔️ Да, отключить", callback_data="/me vk disconnect confirm")]
			]
		),
		query=query
	)

@router.callback_query(Text("/me vk disconnect confirm"), F.message.as_("msg"), F.from_user.as_("user"))
async def me_vk_disconnect_confirm_inline_handler(query: CallbackQuery, msg: Message, user: User) -> None:
	"""
	Inline Callback Handler для команды `/me`.

	Вызывается при нажатии на кнопку "Да, отключить" в меню управления ВКонтакте.
	"""

	telehooper_user = await TelehooperAPI.get_user(user)
	vkService = telehooper_user.get_vk_connection()

	assert vkService

	await vkService.disconnect_service(ServiceDisconnectReason.INITIATED_BY_USER)

	await TelehooperAPI.edit_or_resend_message(
		"<b>⛔️ Отключение ВКонтакте</b>.\n"
		"\n"
		f"Страница «{telehooper_user.connections['VK']['FullName']}» была отключена от Telehooper.\n"
		"\n"
		"ℹ️ Вы можете снова подключиться, введя команду /connect.\n",
		message_to_edit=msg,
		chat_id=msg.chat.id,
		reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔝 В начало", callback_data="/me")]]),
		query=query
	)

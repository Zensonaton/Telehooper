# coding: utf-8

import asyncio
from typing import cast

from aiogram import F, Router, types
from aiogram.filters import Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from pydantic import SecretStr

import utils
from api import TelehooperAPI
from config import config
from services.vk.consts import VK_INVISIBLE_CHARACTER
from services.vk.exceptions import AccountDeactivatedException
from services.vk.service import VKServiceAPI
from services.vk.vk_api.api import VKAPI

from . import utils as vk_utils
from .consts import VK_OAUTH_URL


router = Router()

@router.callback_query(Text("/connect vk"), F.message.as_("msg"))
async def connect_vk_inline_handler(_: types.CallbackQuery, msg: types.Message) -> None:
	"""
	Inline Callback Handler для команды `/connect`.

	Вызывается при выборе "ВКонтакте" в команде `/connect`.
	"""

	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[
			InlineKeyboardButton(text="🔙 Назад", callback_data="/connect"),
			InlineKeyboardButton(text="🔗 Авторизоваться", url=VK_OAUTH_URL)
		]
	])

	await msg.edit_text(
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

@router.message(Text(startswith="https://oauth.vk.com/blank.html#access_token="))
async def connect_vk_token_handler(msg: types.Message) -> None:
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
			"ℹ️ Если Вы уверены, что делаете всё правильно, то создайте Github Issue у репозитория Telehooper, ссылку можно найти в команде <code>/faq 6</code>.",
		)

		return

	if not msg.from_user:
		return

	user = await TelehooperAPI.get_user(msg.from_user)

	if user.rawDocument["Connections"].get("VK"):
		# TODO: Автоматически отключать предыдущий аккаунт ВКонтакте, если он был подключён.
		# Либо же дать такую опцию пользователю.

		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			f"К Telehooper уже <a href=\"vk.com/id{user.rawDocument['Connections']['VK']['ID']}\">подключён аккаунт ВКонтакте</a>. Вы не можете подключить сразу несколько аккаунтов одного типа к Telehooper.\n"
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
		auth_result = await authorize_by_token(cast(types.User, msg.from_user), token)

		# Сохраняем в базу данных сессию пользователя.
		# TODO: НЕ сохранять в БД информацию о подключении, если на это есть настройка.
		user.rawDocument["Connections"]["VK"] = {
			"Token": utils.encrypt_with_env_key(token.get_secret_value()),
			"ConnectedAt": utils.get_timestamp(),
			"LastActivityAt": utils.get_timestamp(),
			"ID": auth_result["id"],
			"OwnedDialogues": {}
		}

		await user.rawDocument.save()
	except AccountDeactivatedException as error:
		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			"К сожалению, Ваша страница ВКонтакте является удалённой, замороженной или заблокированной, либо же у аккаунта ВКонтакте не подтверждён номер телефона.\n"
			"\n"
			"ℹ️ Если это утверждение не является правдой, то в таком случае создайте Github Issue, ссылку можно найти в команде <code>/faq 6</code>.",
		)
	except Exception as error:
		logger.exception(f"Ошибка при авторизации у пользователя Telegram {utils.get_telegram_logging_info(msg.from_user)}: {error}")

		await msg.answer(
			"<b>⚠️ Ошибка подключения сервиса ВКонтакте</b>.\n"
			"\n"
			"К сожалению, произошла ошибка при попытке авторизоваться во ВКонтакте. Попробуйте ещё раз позже.\n"
			"\n"
			"ℹ️ Если данная проблема повторяется, в таком случае создайте Github Issue у репозитория Telehooper, ссылку можно найти в команде <code>/faq 6</code>.",
		)
	else:
		_text = (
			"<b>✅ Подключение ВКонтакте — успех</b>.\n"
			"\n"
			"Успешно! Я сумел подключиться к Вашему аккаунту ВКонтакте!\n"
			f"Я рад с Вами познакомиться, <b>{auth_result['first_name']} {auth_result['last_name']}</b>! 🙃\n"
			"\n"
			"ℹ️ Теперь Вы можете «соединить» диалог из ВКонтакте в Telegram используя этого бота. Для более подробной информации обратитесь к команде <code>/help 5</code>."
		)

		# Если у пользователя установлена фотография, то отправляем её вместе с сообщением.
		# В ином случае отправляем только текст.
		if auth_result["has_photo"]:
			await msg.answer_photo(
				photo=auth_result["photo_max"],
				caption=_text
			)
		else:
			await msg.answer(_text)

		# Создаём объект сервиса, а так же сохраняем его в память пользователя Telehooper.
		vkServiceAPI = VKServiceAPI(
			token=token,
			vk_user_id=auth_result["id"]
		)
		user.save_connection(vkServiceAPI)

		await vkServiceAPI.start_listening()

@router.message(Text(startswith="https://oauth.vk.com/authorize"))
async def connect_vk_wrong_url_handler(msg: types.Message) -> None:
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
		"ℹ️ Если у Вас возникли проблемы, то постарайтесь снова прочитать содержимое информации у команды /connect.",
	)

async def authorize_by_token(user: types.User, token: SecretStr) -> dict:
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
					"(техническое поле: telehooperSuccessAuth)"
				)
			)
		except AccountDeactivatedException as error:
			# Ничего не делаем. Данная ошибка обрабатывается в другом месте.

			raise error
		except Exception as error:
			logger.exception(f"Ошибка при отправке сообщения в ЛС к боту Telehooper (id {config.vkbot_notifier_id}): {error}")

	# Отправляем сообщение в диалог «Избранное».
	await vk_api.messages_send(
		peer_id=user_id,
		message=(
			f"⚠️ ВАЖНАЯ ИНФОРМАЦИЯ ⚠️ {VK_INVISIBLE_CHARACTER * 15}\n"
			"\n"
			"Привет! 🙋\n"
			"Если Вы видите это сообщение, то в таком случае значит, что Telegram-бот под названием «Telehooper» был успешно подключён к Вашей странице ВКонтакте. Пользователь, который подключился к вашей странице ВКонтакте сумеет делать следующее:\n"
			f"{VK_INVISIBLE_CHARACTER}• Читать все получаемые и отправляемые сообщения.\n"
			f"{VK_INVISIBLE_CHARACTER}• Отправлять сообщения.\n"
			f"{VK_INVISIBLE_CHARACTER}• Смотреть список диалогов.\n"
			f"{VK_INVISIBLE_CHARACTER}• Просматривать список Ваших друзей, отправлять им сообщения.\n"
			"\n"
			"Telegram-пользователь, который подключил бота к Вашей странице:\n"
			f"{VK_INVISIBLE_CHARACTER}• {utils.get_telegram_logging_info(user, use_url=True)}.\n"
			"\n"
			"⚠ Если это были не Вы, то срочно в настройках подключённых приложений (https://vk.com/settings?act=apps) отключи приложение «Kate Mobile», либо же в этот же диалог пропиши команду «logoff», (без кавычек) и если же тут появится сообщение о успешном отключении, то значит, что бот был отключён.\n"
			"После отключения срочно меняй пароль от ВКонтакте, поскольку произошедшее значит, что кто-то сумел войти в Ваш аккаунт ВКонтакте, либо же Вы забыли выйти с чужого компьютера!\n"
			"\n"
			"ℹ️ В этом диалоге можно делать следующее для управления Telehooper'ом; все команды прописываются без «кавычек»:\n"
			f"{VK_INVISIBLE_CHARACTER}• Проверить, подключён ли Telehooper: «test».\n"
			f"{VK_INVISIBLE_CHARACTER}• Отправить тестовое сообщение в Telegram: «ping».\n"
			f"{VK_INVISIBLE_CHARACTER}• Отключить аккаунт ВКонтакте от Telehooper: «logoff»."
		)
	)

	await asyncio.sleep(1)

	return user_info

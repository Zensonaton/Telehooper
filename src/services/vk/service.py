# coding: utf-8

from __future__ import annotations

import asyncio
from asyncio.exceptions import TimeoutError
from typing import TYPE_CHECKING, Literal, Optional, cast

import aiohttp
import cachetools
import PIL
from aiocouch import Document
from aiogram import Bot
from aiogram.exceptions import (TelegramBadRequest, TelegramForbiddenError,
                                TelegramNetworkError)
from aiogram.types import Audio, BufferedInputFile, CallbackQuery
from aiogram.types import Document as TelegramDocument
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           InputFile, InputMediaAudio, InputMediaDocument,
                           InputMediaPhoto, InputMediaVideo, Message,
                           PhotoSize, Sticker, Video, VideoNote, Voice)
from aiogram.utils.chat_action import ChatActionSender
from loguru import logger
from pydantic import SecretStr
from pyrate_limiter import Limiter, RequestRate

import utils
from config import config
from consts import MAX_UPLOAD_FILE_SIZE_BYTES
from DB import get_user
from services.service_api_base import (BaseTelehooperServiceAPI,
                                       ServiceDialogue,
                                       ServiceDisconnectReason,
                                       TelehooperServiceUserInfo)
from services.vk.consts import VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT
from services.vk.exceptions import (AccessDeniedException,
                                    TokenRevokedException,
                                    TooManyRequestsException)
from services.vk.utils import (create_message_link, get_attachment_key, get_message_mentions,
                               prepare_sticker)
from services.vk.vk_api.api import VKAPI
from services.vk.vk_api.longpoll import (BaseVKLongpollEvent,
                                         LongpollMessageEditEvent,
                                         LongpollMessageFlagsEdit,
                                         LongpollNewMessageEvent,
                                         LongpollTypingEvent,
                                         LongpollTypingEventMultiple,
                                         LongpollVoiceMessageEvent,
                                         VKAPILongpoll)

if TYPE_CHECKING:
	from api import TelehooperMessage, TelehooperSubGroup, TelehooperUser


class VKServiceAPI(BaseTelehooperServiceAPI):
	"""
	Service API для ВКонтакте. Данный Service API привязан к одному пользователю, и может работать только с его аккаунтом.
	"""

	token: SecretStr
	"""Токен для доступа к API ВКонтакте."""
	vkAPI: VKAPI
	"""Объект для доступа к API ВКонтакте."""

	_cachedDialogues: list = []
	"""Кэшированный список диалогов."""
	_longPollTask: asyncio.Task | None = None
	"""Задача, выполняющая longpoll."""
	_cachedUsersInfo: cachetools.TLRUCache[int, TelehooperServiceUserInfo] # 80 элементов, 5 минут хранения.
	"""Кэшированные данные о пользователях ВКонтакте для быстрого повторного получения."""
	_globalErrorAmount: int
	"""Количество глобальных ошибок. При достижении определённого количества ошибок (см. `VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT`), VK longpoll автоматически отключается от бота."""
	_lastOnlineStatus: int = 0
	"""UNIX-timestamp последнего обновления статуса онлайна через бота. Используется для настройки `Services.VK.SetOnline`."""
	_autoReadChats: dict[int, asyncio.Task]
	"""Словарь, хранящий asyncio.Task для 'прочитывания' сообщений после их отправки собеседником. Используется для настройки `Services.VK.AutoRead`."""

	def __init__(self, token: SecretStr, vk_user_id: int, user: "TelehooperUser", limiter: Limiter = Limiter(RequestRate(2, 1), RequestRate(20, 60))) -> None:
		super().__init__("VK", vk_user_id, user)

		self.token = token
		self.user = user

		self.vkAPI = VKAPI(self.token)

		self.limiter = limiter
		self._cachedUsersInfo = cachetools.TLRUCache(maxsize=80, ttu=lambda _, value, now: now + 5 * 60)
		self._globalErrorAmount = 0
		self._autoReadChats = {}

	async def start_listening(self, bot: Bot | None = None) -> asyncio.Task:
		async def handle_updates() -> None:
			while self._globalErrorAmount < VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT:
				try:
					longpoll = VKAPILongpoll(self.vkAPI, user_id=self.service_user_id)

					async for event in longpoll.listen_for_updates():
						await self.handle_longpoll_update(event)
				except TokenRevokedException as e:
					# Отправляем сообщение, если у нас есть объект бота.
					if bot:
						try:
							await bot.send_message(
								chat_id=self.user.telegramUser.id,
								text=(
									"<b>⚠️ Потеряно соединение с ВКонтакте</b>.\n"
									"\n"
									"Telehooper потерял соединение со страницей «ВКонтакте», поскольку владелец страницы отозвал доступ к ней через настройки «Приватности» страницы.\n"
									"\n"
									"ℹ️ Вы можете повторно подключиться к «ВКонтакте», используя команду /connect.\n"
								)
							)
						except:
							pass

					# Совершаем отключение.
					await self.disconnect_service(ServiceDisconnectReason.EXTERNAL)

					break
				except Exception as error:
					self._globalErrorAmount += 1
					threshold_reached = self._globalErrorAmount >= VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT
					logger.exception(f"Глобальная ошибка #{self._globalErrorAmount}/{VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT} обновления ВКонтакте, со связанным Telegram-пользователем {utils.get_telegram_logging_info(self.user.telegramUser)}:", error)

					# Отправляем сообщение, если у нас есть объект бота.
					if bot:
						upper_text = (
							"Ввиду произошедшей ошибки, какое-то из событий, произошедшее на стороне ВКонтакте могло быть пропущено. 😕\n"
							"\n"
							f"Учтите, бот будет вынужден принудительно отсоединить Вашу страницу от себя если подобная ошибка произойдёт ещё {VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT - self._globalErrorAmount + 1} раз(-а)."
						)
						if threshold_reached:
							upper_text = (
								f"Поскольку Telehooper уже {VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT} раз(-а) сталкивася с ошибками, бот будет вынужден отсоединить Вашу страницу ВКонтакте от себя с целью предотвращения дальнейших ошибок и предупреждений.\n"
								"\n"
								"<b>⚠️ Вы не будете получать новые сообщения в боте Telehooper</b> до тех пор, пока Вы не подключите свою страницу снова."
							)

						try:
							await bot.send_message(
								chat_id=self.user.telegramUser.id,
								text=(
									"<b>⚠️ Ошибка при работе с ВКонтакте</b>.\n"
									"\n"
									"Что-то пошло не так, и Telehooper столкнулся с серьёзной ошибкой при работе с «ВКонтакте».\n"
									f"{upper_text}\n"
									"\n"
									"<b>Текст ошибки, если Вас попросили его отправить</b>:\n"
									f"<code>{error.__class__.__name__}: {error}</code>.\n"
									"\n"
									f"ℹ️ Если проблема не проходит через время - попробуйте попросить помощи либо создать баг-репорт (Github Issue), по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>."

								)
							)
						except:
							pass

			# Если было превышено количество ошибок, то делаем принудительное отключение страницы.
			if self._globalErrorAmount >= VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT:
				logger.warning(f"Telegram-пользователь {utils.get_telegram_logging_info(self.user.telegramUser)} превысил порог в {VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT} глобальных ошибок VK longpoll, совершаю принудительное отключение страницы")

				await self.disconnect_service(ServiceDisconnectReason.ERRORED)

		self._longPollTask = asyncio.create_task(handle_updates())
		return self._longPollTask

	async def handle_longpoll_update(self, event: BaseVKLongpollEvent) -> None:
		"""
		Метод, обрабатывающий события VK Longpoll.

		:param event: Событие, полученное с longpoll-сервера.
		"""

		logger.debug(f"[VK] Новое событие {event.__class__.__name__}: {event.event_data}")

		if type(event) is LongpollNewMessageEvent:
			await self.handle_vk_message(event)
		elif type(event) is LongpollTypingEvent or type(event) is LongpollTypingEventMultiple or type(event) is LongpollVoiceMessageEvent:
			await self.handle_vk_typing(event)
		elif type(event) is LongpollMessageEditEvent:
			await self.handle_vk_message_edit(event)
		elif type(event) is LongpollMessageFlagsEdit:
			await self.handle_vk_message_flags_change(event)
		else:
			logger.warning(f"[VK] Метод handle_update столкнулся с неизвестным событием {event.__class__.__name__}: {event.event_data}")

	async def get_message_prefix(self, event: LongpollNewMessageEvent | LongpollMessageEditEvent, is_outbox: bool, sent_via_bot: bool = False) -> str:
		"""
		Возвращает префикс для отправляемого (или редактируемого) сообщения. Такой префикс выглядит как:
		- `[Вы]: `.
		- `[Имя Ф.]`
		"""

		use_compact_names = await self.user.get_setting("Services.VK.CompactNames")
		ignore_outbox_debug = config.debug and await self.user.get_setting("Debug.SentViaBotInform")
		is_convo = event.peer_id > 2e9
		from_self = (not is_convo and is_outbox) or (is_convo and event.from_id and event.from_id == self.service_user_id)

		# В случае, если мы находимся в ЛС, то префикс никакой не нужен.
		if not (from_self or is_convo):
			return ""

		msg_prefix = "["

		if from_self:
			msg_prefix += "<b>Вы</b>"

			if sent_via_bot and ignore_outbox_debug:
				msg_prefix += " <i>debug-пересылка</i>"
		elif is_convo:
			assert event.from_id, "from_id не был получен, хотя должен присутствовать"

			# Получаем информацию о пользователе, который отправил сообщение.
			sent_user_info = await self.get_user_info(event.from_id)

			msg_prefix += f"<b>{utils.compact_name(sent_user_info.name) if use_compact_names else sent_user_info.name}</b>"

		msg_prefix += "]"

		# Проверяем, указан ли текст сообщения. Если да, то для красоты добавляем символ ":":
		# [Вы]: ...
		if event.text if isinstance(event, LongpollNewMessageEvent) else event.new_text:
			msg_prefix += ": "

		return msg_prefix

	async def handle_vk_message(self, event: LongpollNewMessageEvent) -> None:
		"""
		Обработчик полученных новых сообщений во ВКонтакте.

		:param event: Событие типа `LongpollNewMessageEvent`, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(self.user, ServiceDialogue(service_name=self.service_name, id=event.peer_id))

		# Проверяем, что у пользователя есть подгруппа, в которую можно отправить сообщение.
		if not subgroup:
			return

		async def handle_message_events() -> None:
			issuer_name_with_link = None
			issuer_male = True
			victim_name_with_link = None
			victim_male = True

			if event.from_id:
				issuer_info = await self.get_user_info(event.from_id)

				issuer_name_with_link = f"<a href=\"{'m.' if use_mobile_vk else ''}vk.com/id{event.from_id}\">{utils.compact_name(issuer_info.name) if use_compact_names else issuer_info.name}</a>"
				issuer_male = issuer_info.male or False

			if event.source_mid:
				victim_info = await self.get_user_info(event.source_mid)

				victim_name_with_link = f"<a href=\"{'m.' if use_mobile_vk else ''}vk.com/id{event.source_mid}\">{utils.compact_name(victim_info.name) if use_compact_names else victim_info.name}</a>"
				victim_male = victim_info.male or False

			event_action = cast(str, event.source_act)

			# Во ВКонтакте, событие "X вернулся/вышел из беседы" работает как
			# "X пригласил/исключил X из беседы", поэтому здесь такая проверка.
			if event.from_id == event.source_mid and event_action in ["chat_invite_user", "chat_kick_user"]:
				event_action = "chat_return" if event_action == "chat_invite_user" else "chat_leave"

			messages = {
				"chat_photo_update": f"{issuer_name_with_link} обновил{'' if issuer_male else 'а'} фотографию беседы",
				"chat_photo_remove": f"{issuer_name_with_link} удалил{'' if issuer_male else 'а'} фотографию беседы",
				"chat_create": f"{issuer_name_with_link} создал{'' if issuer_male else 'а'} новую беседу: «{event.source_text}»",
				"chat_title_update": f"{issuer_name_with_link} изменил{'' if issuer_male else 'а'} имя беседы на «{event.source_text}»",
				"chat_invite_user": f"{issuer_name_with_link} добавил{'' if issuer_male else 'а'} пользователя {victim_name_with_link}",
				"chat_kick_user": f"{issuer_name_with_link} удалил{'' if issuer_male else 'а'} пользователя {victim_name_with_link} из беседы",
				"chat_invite_user_by_link": f"{victim_name_with_link} присоеденил{'ся' if issuer_male else 'ась'} к беседе используя пригласительную ссылку",
				"chat_invite_user_by_message_request": f"{victim_name_with_link} присоденил{'ся' if issuer_male else 'ась'} к беседе используя запрос на вступление",
				"chat_pin_message": f"{issuer_name_with_link} закрепил{'' if issuer_male else 'а'} сообщение",
				"chat_unpin_message": f"{issuer_name_with_link} открепил{'' if issuer_male else 'а'} закреплённое сообщение",
				"chat_screenshot": f"{victim_name_with_link} сделал{'' if issuer_male else 'а'} скриншот чата",
				"conversation_style_update": f"{issuer_name_with_link} обновил стиль чата",
				"chat_leave": f"{issuer_name_with_link} покинул{'' if issuer_male else 'а'} беседу",
				"chat_return": f"{issuer_name_with_link} вернул{'ся' if issuer_male else 'ась'} в беседу",
				# "call_ended": f"{victim_name_with_link} начал{'' if issuer_male else 'а'} вызов ВКонтакте. Присоедениться можно <a href=\"https://vk.com/call/join/{group_chat_join_link}\">по ссылке</a>"
			}
			message = messages.get(event_action)

			if not message:
				logger.warning(f"[VK] Неизвестное событие беседы: {event_action}")

				message = f"Неизвестное действие: <code>«{event_action}»</code>"

				return

			# Здесь мы не сохраняем ID сообщения, поскольку с таковыми в любом случае нельзя взаимодействовать.
			await subgroup.send_message_in(f"ℹ️  <i>{message}</i>", disable_web_preview=True)

			# Если пользователь разрешил синхронизацию изменений в беседе, то делаем их.
			if await self.user.get_setting("Services.VK.SyncGroupInfo"):
				if event_action == "chat_title_update":
					assert event.source_text, "Новое имя беседы не было получено"

					title = event.source_text
					if config.debug and await self.user.get_setting("Debug.DebugTitleForDialogues"):
						title = f"[DEBUG] {title}"

					await subgroup.parent.set_title(title)
				elif event_action == "chat_photo_update":
					assert message_extended, "Не удалось получить информацию о сообщении"

					async with aiohttp.ClientSession() as client:
						async with client.get(message_extended["attachments"][0]["photo"]["sizes"][-1]["url"]) as response:
							assert response.status == 200, "Не удалось загрузить фотографию беседы"

							photo_bytes = await response.read()

					await subgroup.parent.set_photo(BufferedInputFile(photo_bytes, filename="VK chat photo.jpg"))
				elif event_action == "chat_photo_remove":
					await subgroup.parent.remove_photo()
				elif event_action in ["chat_pin_message", "chat_unpin_message"]:
					assert event.source_chat_local_id, "ID сообщения, которое было прикреплено не было получено"

					# Пытаемся найти полную информацию о сообщении.
					message_data = (await self.vkAPI.messages_getByConversationMessageId(peer_id=event.peer_id, conversation_message_ids=event.source_chat_local_id))["items"]

					if message_data:
						vk_message_id = message_data[0]["id"]

						telegram_message = await subgroup.service.get_message_by_service_id(self.service_user_id, vk_message_id)
						if not telegram_message:
							return

						if event_action == "chat_pin_message":
							# Открепляем старое сообщение.
							try:
								await subgroup.parent.unpin_message()
							except:
								pass

							await subgroup.parent.pin_message(telegram_message.telegram_message_ids[0])
						else:
							await subgroup.parent.unpin_message(telegram_message.telegram_message_ids[0])

		logger.debug(f"[VK] Сообщение с текстом \"{event.text}\", для подгруппы \"{subgroup.service_dialogue_name}\"")

		message_url = None
		keyboard = None
		try:
			attachment_media: list[InputMediaAudio | InputMediaDocument | InputMediaPhoto | InputMediaVideo] = []
			attachment_items: list[str] = []
			use_compact_names = await self.user.get_setting("Services.VK.CompactNames")
			use_mobile_vk = await self.user.get_setting("Services.VK.MobileVKURLs")
			message_url = create_message_link(event.peer_id, event.message_id, use_mobile=use_mobile_vk)
			ignore_outbox_debug = config.debug and await self.user.get_setting("Debug.SentViaBotInform")
			is_outbox = event.flags.outbox
			is_inbox = not is_outbox
			is_group = event.peer_id < 0
			is_convo = event.peer_id > 2e9
			is_user = not is_group and not is_convo
			is_bot = (event.from_id or 0) < 0
			from_self = (not is_convo and is_outbox) or (is_convo and event.from_id and event.from_id == self.service_user_id)
			message_text_stripped = event.text.lower().strip()

			# Проверяем, стоит ли боту обрабатывать исходящие сообщения.
			if is_outbox and not (ignore_outbox_debug or await self.user.get_setting("Services.VK.ViaServiceMessages")):
				return

			# Проверяем, не было ли отправлено сообщение через бота.
			# Для этого нужно получить информацию о полученном сообщении.
			#
			# Здесь происходит очень забавная вещь:
			# На моём личном сервере, бот получает Longpoll-событие о новом сообщении ранее
			# момента получения ответа API запроса messages.send с ID отправленного сообщения.
			#
			# Выглядит это примерно так:
			# [messages.send req] <...> [longpoll new msg event] <...> [messages.send response]
			#
			# Ввиду этого, бот получает новое событие, и думает, что оно не было
			# отправлено через бота (поскольку ID сообщения ещё не был получен).
			#
			# Что бы конпенсировать это, бот вынужден проверить наличие текста сообщения в preMessageCache,
			# который пополняется текстами отправленных через бота сообщений, и если такое сообщение
			# и вправду есть, то бот считает, что это сообщение было отправлено через бота.
			# В ином случае, приходится делать небольшую задержку, что бы убедиться, что messages.send,
			# выполняемый асинхронно, вернул ID сообщения.
			#
			# Спонсор сегодняшних костылей - асинхронность.
			if message_text_stripped in subgroup.pre_message_cache:
				sent_via_bot = True

				# Удаляем сообщение из кэша, поскольку проверка уже была проведена.
				subgroup.pre_message_cache.pop(message_text_stripped)
			else:
				# Причина существования этого sleep описана выше.
				await asyncio.sleep(0.2)

				# Проверяем на наличие сохранённого сообщения.
				msg_saved = await subgroup.service.get_message_by_service_id(self.service_user_id, event.message_id)

				sent_via_bot = msg_saved and msg_saved.sent_via_bot

			if sent_via_bot and not ignore_outbox_debug:
				return

			# Добываем полную информацию о сообщении.
			message_extended = (await self.vkAPI.messages_getById(event.message_id))["items"][0]

			# Получаем ID сообщения с ответом, а так же парсим вложения сообщения.
			reply_to = None
			if event.attachments or is_group or is_bot:
				attachments = event.attachments.copy()

				# Обрабатываем ответы (reply).
				if "reply" in attachments or ("fwd_messages" in message_extended and len(message_extended["fwd_messages"]) == 1 and await self.user.get_setting("Services.VK.FWDAsReply")):
					reply_vk_message_id: int | None = message_extended["reply_message"].get("id") if "reply" in attachments else None
					fwd_vk_message_id: int | None = message_extended["fwd_messages"][0].get("id") if "reply" not in attachments else None
					fwd_vk_conversation_message_id: int | None = message_extended["fwd_messages"][0].get("conversation_message_id") if "reply" not in attachments else None

					# В некоторых случаях ID reply может отсутствовать,
					# вместо него либо ничего нет, либо есть conversation message id.
					if not (reply_vk_message_id or fwd_vk_message_id or fwd_vk_conversation_message_id):
						logger.warning(f"[VK] Пользователь сделал Reply на сообщение во ВКонтакте, однако API ВКонтакте не вернул ID сообщения, на который был сделан Reply. Сообщение: {message_extended}")
					elif fwd_vk_conversation_message_id:
						# Нам дан Conversation Message ID, ищем "реальный" ID сообщения.
						message_data = (await self.vkAPI.messages_getByConversationMessageId(event.peer_id, fwd_vk_conversation_message_id))["items"]

						if message_data:
							reply_vk_message_id = message_data[0]["id"]
					elif fwd_vk_message_id:
						# Была сделана пересылка сообщения, в таком случае используем ID данного сообщения.
						reply_vk_message_id = fwd_vk_message_id

					# Настоящий ID сообщения, на которое был дан ответ, получен. Получаем информацию о сообщении с БД бота.
					if reply_vk_message_id:
						telegram_message = await subgroup.service.get_message_by_service_id(self.service_user_id, reply_vk_message_id)

						# Если информация о данном сообщении есть, то мы можем получить ID сообщения в Telegram.
						if telegram_message:
							reply_to = telegram_message.telegram_message_ids[0]

				# Обрабатываем клавиатуру.
				if "keyboard" in message_extended:
					buttons = []

					for row in message_extended["keyboard"]["buttons"]:
						current_row = []

						for button in row:
							button_type = button["action"]["type"]

							if button_type in ["text", "callback"]:
								current_row.append(
									InlineKeyboardButton(
										text=button["action"]["label"],
										callback_data=subgroup.create_callback_btn(button["action"]["payload"])
									)
								)
							elif button_type == "open_link":
								current_row.append(
									InlineKeyboardButton(
										text=button["action"]["label"],
										url=button["action"]["link"]
									)
								)
							elif button_type == "location":
								current_row.append(
									InlineKeyboardButton(
										text=f"[отправка местоположения]",
										url=message_url
									)
								)
							elif button_type == "vkpay":
								current_row.append(
									InlineKeyboardButton(
										text=f"[платёж VKPay]",
										url=message_url
									)
								)
							else:
								logger.warning(f"[VK] Неизвестный тип action для кнопки: \"{button_type}\"")

								current_row.append(
									InlineKeyboardButton(
										text=f"❔ Кнопка типа {button_type}",
										url=message_url
									)
								)

						buttons.append(current_row)

					keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

				# Обрабатываем пересланные.
				if message_extended.get("fwd_messages") and not reply_to:
					fwd_messages = message_extended["fwd_messages"]

					attachment_items.append(f"<a href=\"{message_url}\">🔁 {'Пересланное сообщение' if len(fwd_messages) == 1 else str(len(fwd_messages)) + ' пересланных сообщений'}</a>")

				# Обрабатываем гео-вложения.
				if "geo" in attachments:
					attachment = message_extended["geo"]

					# Высылаем сообщение.
					msg = await subgroup.send_geo(
						latitude=attachment["coordinates"]["latitude"],
						longitude=attachment["coordinates"]["longitude"],
						silent=is_outbox,
						reply_to=reply_to,
						sender_id=event.from_id if event.from_id != self.service_user_id else None
					)

					# Если произошёл rate limit, то msg будет None.
					if not msg:
						return

					await TelehooperAPI.save_message(
						"VK",
						self.service_user_id,
						msg[0].message_id,
						event.message_id,
						message_extended["conversation_message_id"],
						sent_via_bot=False
					)

					return

				# Проходимся по всем вложениям.
				if message_extended and "attachments" in message_extended:
					for attch_index, attachment in enumerate(message_extended["attachments"]):
						attachment_type = attachment["type"]
						attachment = attachment[attachment["type"]]

						if attachment_type == "photo":
							# Проходимся по всем размерам фотографии и выбираем самый большой.
							sizes_sorted = sorted(attachment["sizes"], key=lambda size: size["width"] * size["height"], reverse=True)

							attachment_media.append(
								InputMediaPhoto(
									type="photo",
									media=sizes_sorted[0]["url"]
								)
							)
						elif attachment_type == "video":
							# Так как ВК не выдают прямую ссылку на видео, необходимо её извлечь из API.
							# Что важно, передать ссылку напрямую не получается, поскольку ВК проверяет
							# UserAgent и IP адрес, с которого был сделан запрос.

							# Проверяем, видеосообщение (кружочек) ли это?
							is_video_note = attachments.get(f"attach{attch_index + 1}_kind") == "video_message"

							async with ChatActionSender(chat_id=subgroup.parent.chat.id, action="upload_video", bot=subgroup.parent.bot):
								video = (await self.vkAPI.video_get(videos=get_attachment_key(attachment)))["items"][0]
								if "files" not in video:
									# В случаях, если видео помечено как "доступно только подписчикам", ВК не даёт ссылок на скачивание.
									# В таких случаях мы просто отображаем видео как ссылку на него.

									attachment_items.append(f"<a href=\"{'m.' if use_mobile_vk else ''}vk.com/wall{video['owner_id']}_{attachment['id']}\">📹 Видео с закрытым доступом</a>")

									continue

								video = video["files"]

								# Если это внешнее видео (т.е., ссылка на Youtube или подобное),
								# то в таком случае прямых ссылок на файлы будут отсутствовать.
								#
								# В таком случае нужно просто добавить ссылку на видео как вложение.
								if "external" in video:
									attachment_items.append(f"<a href=\"{video['external']}\">📹 Внешнее видео</a>")

									continue

								# Делаем список из возможных качеств для видео.
								video_quality_list = ["mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240", "mp4_144"]
								video_hd_quality_list = ["mp4_1080"]

								# Составляем список качеств видео, которые были переданы ВКонтакте.
								present_video_quality_list = [quality for quality in video_quality_list if quality in video]

								# Узнаём, разрешены ли HD-видео.
								hd_video_allowed = await self.user.get_setting("Services.VK.HDVideo")

								for quality in present_video_quality_list:
									is_last = quality == present_video_quality_list[-1]
									is_hd = quality in video_hd_quality_list

									# Нам нужно убедиться, что если это HD видео, и есть видео другого качества,
									# то в таком случае нужно пропустить такой формат.
									if is_hd and not is_last and not hd_video_allowed:
										continue

									logger.debug(f"Найдено видео с качеством {quality}: {video[quality]}")

									# Загружаем видео.
									async with aiohttp.ClientSession() as client:
										async with client.get(video[quality]) as response:
											assert response.status == 200, f"Не удалось загрузить видео с качеством {quality}"

											content_size = int(response.headers.get("Content-Length", "0"))
											assert content_size, "Не был выдан размер файла для загрузки"

											# Пытаемся найти самое большое видео, размер которого не превышает 50 МБ.
											if content_size > MAX_UPLOAD_FILE_SIZE_BYTES:
												if is_last:
													raise Exception("Не было найдено видео меньшего размера")

												logger.debug(f"Файл качества {quality} оказался слишком большой ({content_size} байт).")

												continue

											# По-настоящему загружаем видео.
											video_bytes = await response.read()

									# Если мы получили видеосообщение (кружочек), то нужно отправить его как сообщение.
									if is_video_note:
										# Отправляем видеосообщение.
										msg = await subgroup.send_video_note(
											input=BufferedInputFile(video_bytes, filename=f"VK video note {attachment['id']}.mp4"),
											silent=is_outbox,
											reply_to=reply_to,
											sender_id=event.from_id if event.from_id != self.service_user_id else None
										)

										# Если произошёл rate limit, то msg будет None.
										if not msg:
											return

										# Сохраняем в память.
										await TelehooperAPI.save_message(
											"VK",
											self.service_user_id,
											msg[0].message_id,
											event.message_id,
											message_extended["conversation_message_id"],
											sent_via_bot=False
										)

										assert msg[0].video_note, "Видеосообщение не было отправлено"

										return

									# Прикрепляем видео.
									attachment_media.append(
										InputMediaVideo(
											type="video",
											media=BufferedInputFile(
												video_bytes,
												filename=f"{attachment['title'].strip()} {quality[4:]}p.mp4"
											)
										)
									)

									break
								else:
									raise Exception("ВКонтакте не вернул ссылку на видео")
						elif attachment_type == "audio_message":
							attachment_media.append(
								InputMediaAudio(
									type="audio",
									media=attachment["link_ogg"]
								)
							)
						elif attachment_type == "sticker":
							async def _downloadSticker(url: str, is_animated: bool) -> bytes:
								"""
								Загружает стикер по указанному URL.

								Если стикер является анимированным, то данный метод его ещё и сконвертирует в формат .tgs.

								:param url: URL на данный файл со стикером.
								:param is_animated: Указывает, что после загрузки стикера он должен сконвертироваться в формат .tgs.
								"""

								logger.debug(f"Загружаю стикер с URL {url}")

								async with aiohttp.ClientSession() as client:
									async with client.get(sticker_url) as response:
										assert response.status == 200, f"Не удалось загрузить стикер с ID {attachment_cache_name}"

										sticker_bytes = await response.read()

								if is_animated:
									sticker_bytes = await utils.convert_to_tgs_sticker(sticker_bytes)

								return sticker_bytes

							# В данный момент, поддержка анимированных стикеров отсутствует из-за особенности в сжатии библиотеки gzip.
							is_animated = "animation_url" in attachment
							sticker_url = attachment.get("animation_url") if is_animated else attachment["images"][-1]["url"]
							attachment_cache_name = f"sticker{attachment['sticker_id']}{'anim' if is_animated else 'static'}"

							# Пытаемся получить информацию о данном стикере из кэша вложений.
							sticker_bytes = None
							cached_sticker = await TelehooperAPI.get_attachment("VK", attachment_cache_name)

							# Если стикер был найден в кэше, то скачиваем его.
							if not cached_sticker:
								logger.debug(f"Не был найден кэш для стикера с ID {attachment_cache_name}")

								# Загружаем стикер.
								sticker_bytes = await _downloadSticker(sticker_url, is_animated)

							# Отправляем стикер.
							# Иногда стикеры, сохранённые в кэше ломаются. Если такое происходит, то бот удаляет стикер из кэша.
							try:
								msg = await subgroup.send_sticker(
									sticker=cached_sticker if cached_sticker else BufferedInputFile(
										file=cast(bytes, sticker_bytes),
										filename="sticker.tgs" if is_animated else f"VK sticker {attachment['sticker_id']}.png"
									),
									silent=is_outbox,
									reply_to=reply_to,
									sender_id=event.from_id if event.from_id != self.service_user_id else None
								)
							except TelegramBadRequest:
								# Поскольку кэш стикера оказался поломанным, стоит отправить стикер по-новой, игнорируя кэш.
								await TelehooperAPI.delete_attachment("VK", attachment_cache_name)
								sticker_bytes = await _downloadSticker(sticker_url, is_animated)

								msg = await subgroup.send_sticker(
									sticker=BufferedInputFile(
										file=cast(bytes, sticker_bytes),
										filename="sticker.tgs" if is_animated else f"VK sticker {attachment['sticker_id']}.png"
									),
									silent=is_outbox,
									reply_to=reply_to,
									sender_id=event.from_id if event.from_id != self.service_user_id else None
								)

							# Если произошёл rate limit, то msg будет None.
							if not msg:
								return

							assert msg[0].sticker, "Стикер не был отправлен"

							# Сохраняем в память.
							await TelehooperAPI.save_message(
								"VK",
								self.service_user_id,
								msg[0].message_id,
								event.message_id,
								message_extended["conversation_message_id"],
								sent_via_bot=False
							)

							# Кэшируем стикер, если настройка у пользователя это позволяет.
							if not cached_sticker and await self.user.get_setting("Security.MediaCache"):
								await TelehooperAPI.save_attachment(
									"VK",
									attachment_cache_name,
									msg[0].sticker.file_id
								)

							return
						elif attachment_type == "doc":
							async with ChatActionSender(chat_id=subgroup.parent.chat.id, action="upload_document", bot=subgroup.parent.bot):
								async with aiohttp.ClientSession() as client:
									async with client.get(attachment["url"]) as response:
										assert response.status == 200, f"Не удалось загрузить документ с ID {attachment['id']}"

										content_size = int(response.headers.get("Content-Length", "0"))
										assert content_size, "Не был выдан размер файла для загрузки"

										# Проверяем, не превышает ли размер файла 50 МБ.
										if content_size > MAX_UPLOAD_FILE_SIZE_BYTES:
											logger.debug(f"Файл оказался слишком большой ({content_size} байт).")

											raise Exception("Размер файла слишком большой")

										# По-настоящему загружаем документ.
										file_bytes = await response.read()

								# Прикрепляем документ.
								attachment_media.append(InputMediaDocument(type="document", media=BufferedInputFile(file=file_bytes, filename=attachment["title"])))
						elif attachment_type == "audio":
							# Обрабатываем музыку.

							# В некоторых случаях, ВК может не передавать ссылку на аудио.
							# В таком случае, бот просто прикрепит музыку как текстовое вложение.
							if not attachment.get("url"):
								attachment_items.append(f"<a href=\"{message_url}\">🎵 {attachment['artist']} - {attachment['title']}</a>")

								continue

							async with ChatActionSender(chat_id=subgroup.parent.chat.id, action="upload_audio", bot=subgroup.parent.bot):
								async with aiohttp.ClientSession() as client:
									async with client.get(attachment["url"]) as response:
										assert response.status == 200, f"Не удалось загрузить аудио с ID {attachment['id']}"

										content_size = int(response.headers.get("Content-Length", "0"))
										assert content_size, "Не был выдан размер файла для загрузки"

										# Проверяем, не превышает ли размер файла 50 МБ.
										if content_size > MAX_UPLOAD_FILE_SIZE_BYTES:
											logger.debug(f"Файл оказался слишком большой ({content_size} байт).")

											raise Exception("Размер файла слишком большой")

										# По-настоящему загружаем аудио.
										file_bytes = await response.read()

								attachment_media.append(
									InputMediaAudio(
										type="audio",
										media=BufferedInputFile(
											file=file_bytes,
											filename=f"{attachment['artist']} - {attachment['title']}.mp3"
										),
										title=attachment["title"],
										performer=attachment["artist"]
									)
								)
						elif attachment_type == "graffiti":
							attachment_media.append(
								InputMediaPhoto(
									type="photo",
									media=attachment["url"]
								)
							)
						elif attachment_type == "wall":
							# TODO: Имя группы/юзера откуда был пост.
							#   В данный момент почти нереализуемо из-за того, что ВК не передаёт такую информацию, и нужно делать отдельный запрос.
							# TODO: Настройка, что бы показывать содержимое поста, а не ссылку на него.

							attachment_items.append(f"<a href=\"{'m.' if use_mobile_vk else ''}vk.com/wall{attachment['owner_id']}_{attachment['id']}\">🔄 Запись от {'пользователя' if attachment['owner_id'] > 0 else 'группы'}</a>")
						elif attachment_type == "link":
							# TODO: Проверить, какая первая ссылка есть в сообщении, и если она не совпадает с этой - сделать невидимую ссылку в самом начале.

							pass
						elif attachment_type == "poll":
							attachment_items.append(f"<a href=\"{message_url}\">📊 Опрос: «{attachment['question']}»</a>")
						elif attachment_type == "gift":
							attachment_media.append(InputMediaPhoto(type="photo", media=attachment["thumb_256"]))

							attachment_items.append(f"<a href=\"{message_url}\">🎁 Подарок</a>")
						elif attachment_type == "market":
							attachment_items.append(f"<a href=\"{message_url}\">🛒 Товар: «{attachment['title']}»</a>")
						elif attachment_type == "market_album":
							pass
						elif attachment_type == "wall_reply":
							attachment_items.append(f"<a href=\"{message_url}\">📝 Комментарий к записи</a>")
						elif attachment_type == "story":
							attachment_items.append(f"<a href=\"{message_url}\">📝 История</a>")
						else:
							raise TypeError(f"Неизвестный тип вложения \"{attachment_type}\"")

			# Проверяем, не было ли это событие беседы из ВК.
			if is_convo and event.source_act:
				await handle_message_events()

				return

			# Подготавливаем текст сообщения, который будет отправлен.
			msg_prefix = await self.get_message_prefix(event, is_outbox)
			msg_body = utils.telegram_safe_str(event.text)
			msg_suffix = ""

			# Добавляем ссылки на вложения.
			if attachment_items:
				msg_suffix += "\n\n————————\n"

				msg_suffix += "  |  ".join(attachment_items) + "."

			# Делаем обработку упоминаний вида:
			#  "Привет, [id1|Дуров]!"
			# ->
			#  "Привет, Дуров!" (с ссылкой)
			msg_mentions = get_message_mentions(msg_body)

			for domain, mention_text in msg_mentions:
				original_mention_text = f"[{domain}|{mention_text}]"

				assert original_mention_text in msg_body, "Не получилось восстановить текст упоминания для замены"

				# Извлекаем ID упоминаемого пользователя/группы, что бы получить информацию о нём (domain/username, полное имя).
				mention_id = int(domain[2:]) if "id" in domain else -int(int(domain[4:]))

				# Делаем API-запрос, получая информацию о пользователе.
				mention_info = await self.get_user_info(mention_id)

				# Создаём ссылку на страницу пользователя.
				#
				# В ссылке так же передаётся имя и фамилия упоминаемого пользвателя, это нужно
				# что бы при нажатии на упоминание, клиенты Telegram показывали ссылку вида:
				#   https://vk.com/durov?Павел_Дуров
				mention_user_url = (
					f"https://{'m.' if use_mobile_vk else ''}vk.com/"
					f"{mention_info.username or domain}"
					f"?{mention_info.name.replace(' ', '_')}"
				)

				msg_body = msg_body.replace(
					original_mention_text,
					f"<a href=\"{mention_user_url}\">{mention_text}</a>"
				)

			full_message_text = msg_prefix + msg_body + msg_suffix

			# Отправляем готовое сообщение, и сохраняем его ID в БД бота.
			async def _send_and_save(force_manual_files_upload: bool = False) -> None:
				"""
				Высылает сообщение в Telegram, а так же сохраняет их ID в БД.

				:param force_manual_files_upload: Если True, то вместо передачи прямого URL на вложения, бот будет их загружать вручную.
				"""

				attachment_media_downloaded = attachment_media

				# Загружаем вложения вручную, если это указано.
				if force_manual_files_upload:
					logger.debug("Пытаюсь вручную загрузить вложения...")

					for index, attachment in enumerate(attachment_media_downloaded):
						if isinstance(attachment.media, InputFile):
							continue

						logger.debug(f"Вручную загружаю вложение {attachment}...")

						# TODO: Сделать asyncio.gather() для загрузки всех вложений одновременно.
						async with aiohttp.ClientSession() as session:
							async with session.get(attachment.media) as response:
								assert response.status == 200, f"Не удалось загрузить вложение с URL {attachment.media}"

								attachment_bytes = await response.read()

						# Вложение загружено, меняем в массиве с вложениями.
						attachment_media_downloaded[index].media = BufferedInputFile(
							file=attachment_bytes,
							filename="Media"
						)

				# Высылаем сообщение.
				#
				# К сожалению, Telegram не позволяет отправлять сообщения с одновременно
				# аудио/документами и другими видами вложений. Что бы избежать ошибки,
				# данный код отдельно отправляет сообщение без аудио, а потом - с аудио.
				audio_attachments = [i for i in attachment_media_downloaded if isinstance(i, InputMediaAudio)]
				doc_attachments = [i for i in attachment_media_downloaded if isinstance(i, InputMediaDocument)]
				normal_attachments = [i for i in attachment_media_downloaded if i not in audio_attachments and i not in doc_attachments]

				separate_attachs = normal_attachments and (audio_attachments or doc_attachments)

				sent_message_ids = []
				msg_special = await subgroup.send_message_in(
					full_message_text,
					attachments=normal_attachments or audio_attachments or doc_attachments, # type: ignore
					silent=is_outbox,
					reply_to=reply_to,
					keyboard=keyboard,
					sender_id=event.from_id if event.from_id != self.service_user_id else None
				)

				# Если произошёл rate limit, то ответ на отправку сообщений будет равен None.
				if not msg_special:
					return

				sent_message_ids.extend(msg_special)

				# В случае необходимости, отправляем "особые" виды вложений по-отдельности.
				if separate_attachs:
					# Аудио, если нужны:
					msg_audio = await subgroup.send_message_in(
						"ℹ️ <i>Данное сообщение было разделено ввиду ограничений Telegram, данное сообщение — часть сообщения, на которое был сделан «ответ»</i>.",
						attachments=audio_attachments, # type: ignore
						silent=is_outbox,
						reply_to=msg_special[0],
						sender_id=event.from_id if event.from_id != self.service_user_id else None
					)

					if msg_audio:
						sent_message_ids.extend(msg_audio)

					# Документы, если нужны:
					msg_docs = await subgroup.send_message_in(
						"ℹ️ <i>Данное сообщение было разделено ввиду ограничений Telegram, данное сообщение — часть сообщения, на которое был сделан «ответ»</i>.",
						attachments=doc_attachments, # type: ignore
						silent=is_outbox,
						reply_to=msg_special[0],
						sender_id=event.from_id if event.from_id != self.service_user_id else None
					)

					if msg_docs:
						sent_message_ids.extend(msg_docs)

				# Если произошёл rate limit, то бот не сможет выслать сообщения,
				# и список из отправленных сообщений будет пуст.
				if not sent_message_ids:
					return

				await TelehooperAPI.save_message(
					"VK",
					self.service_user_id,
					sent_message_ids,
					event.message_id,
					message_extended["conversation_message_id"],
					sent_via_bot=False
				)

			# Отправляем сообщения с вложениями.
			# Для отображения прогресса отправки, бот должен показать пользователям надпись "Telehooper отправляет документ...".
			async with ChatActionSender.upload_document(chat_id=subgroup.parent.chat.id, bot=subgroup.parent.bot, initial_sleep=1):
				try:
					await _send_and_save()
				except (TelegramNetworkError, TimeoutError):
					logger.debug("Таймаут при попытке отправить сообщения, пробую загрузить вложения вручную")

					# Что-то пошло не так и произошёл таймаут.
					# Пробуем выслать сообщения ещё раз, но в этот раз бот должен вручную загрузить вложения.
					await _send_and_save(force_manual_files_upload=True)

			# Если это разрешено пользователем, то мы должны запустить таймер для "прочитки" последнего сообщения.
			read_setting_value = cast(Literal["ignore", "single", "multiuser", "all"], await self.user.get_setting(f"Services.{self.service_name}.AutoRead"))

			if (read_setting_value == "single" and not is_convo) or (read_setting_value == "multiuser" and is_convo) or (read_setting_value == "all"):
				# Если задача по "прочитыванию" уже запущена, то останавливаем её.
				if subgroup.service_chat_id in self._autoReadChats:
					self._autoReadChats[subgroup.service_chat_id].cancel()

				# Получаем время, через которое мы должны "прочитать" сообщение.
				read_setting_timer = int(await self.user.get_setting(f"Services.{self.service_name}.AutoReadTime"))

				async def read_task(chat_id: int, timer: int) -> None:
					await asyncio.sleep(timer)

					logger.debug(f"Помечаю чат {chat_id} как прочитанный, поскольку прошло {timer} секунд с момента отправки.")
					try:
						await self.read_message(chat_id)
					except:
						pass

				# Запускаем задачу по "прочитыванию" чата через время.
				self._autoReadChats[subgroup.service_chat_id] = asyncio.create_task(read_task(subgroup.service_chat_id, read_setting_timer))
		except TelegramForbiddenError:
			await TelehooperAPI.delete_group_data(subgroup.parent.chat.id, fully_delete=True, bot=subgroup.parent.bot)
		except Exception as e:
			logger.exception(f"Ошибка отправки сообщения Telegram-пользователю {utils.get_telegram_logging_info(self.user.telegramUser)}:", e)

			try:
				await subgroup.send_message_in(
					(
						"<b>⚠️ Ошибка при отправке сообщения</b>.\n"
						"\n"
						"<i><b>Упс!</b></i> Что-то пошло не так, и бот столкнулся с ошибкой при попытке переслать сообщение из ВКонтакте. 😓\n"
						f"Вы можете прочитать сообщение во ВКонтакте, перейдя <a href=\"{message_url}\">по ссылке</a>.\n"
						"\n"
						"<b>Текст ошибки, если Вас попросили его отправить</b>:\n"
						f"<code>{e.__class__.__name__}: {e}</code>.\n"
						"\n"
						f"ℹ️ Пожалуйста, подождите, перед тем как попробовать снова. Если проблема не проходит через время - попробуйте попросить помощи либо создать баг-репорт (Github Issue), по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>."
					),
					silent=True,
					keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
						text="Открыть сообщение во ВКонтакте",
						url=message_url
					)]])
				)
			except:
				pass

	async def handle_vk_typing(self, event: LongpollTypingEvent | LongpollTypingEventMultiple | LongpollVoiceMessageEvent) -> None:
		"""
		Обработчик события начала "печати" либо записи голосового сообщения во ВКонтакте.

		:param event: Событие типа `LongpollTypingEvent`, `LongpollTypingEventMultiple` или `LongpollVoiceMessageEvent`, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(self.user, ServiceDialogue(service_name=self.service_name, id=event.peer_id))

		# Проверяем, что у пользователя есть подгруппа, в которой нужно начать событие печати.
		if not subgroup:
			return

		# Получаем список всех "печатающих" пользователей.
		typing_users: list[int] = []
		if isinstance(event, LongpollTypingEvent):
			typing_users = [event.user_id]
		elif isinstance(event, LongpollTypingEventMultiple) or isinstance(event, LongpollVoiceMessageEvent):
			typing_users = [event.user_ids] if isinstance(event.user_ids, int) else event.user_ids

		logger.debug(f"[VK] Событие печати для подгруппы \"{subgroup.service_dialogue_name}\", {len(typing_users)} печатающих")

		try:
			for user_id in typing_users:
				await subgroup.start_activity(
					"record_audio" if type(event) is LongpollVoiceMessageEvent else "typing",
					sender_id=user_id if user_id != subgroup.service.service_user_id else None
				)
		except TelegramForbiddenError:
			await TelehooperAPI.delete_group_data(
				subgroup.parent.chat.id,
				fully_delete=True,
				bot=subgroup.parent.bot
			)

	async def handle_vk_message_edit(self, event: LongpollMessageEditEvent) -> None:
		"""
		Обработчик события редактирования сообщения во ВКонтакте.

		:param event: Событие типа `LongpollMessageEditEvent`, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(self.user, ServiceDialogue(service_name=self.service_name, id=event.peer_id))

		# Проверяем, что у пользователя есть подгруппа, в которую можно отправить сообщение.
		if not subgroup:
			return

		# Уродливая проверка, поскольку ВК по какой-то причине "редактирует" сообщение при его закрепе.
		#
		# В моём случае, ничего не будет происходить, если "редактирование" имеет
		# поле "pinned_at", и разница между текущим и этим временем менее 2 секунды.
		# Возможно, это не самый лучший способ, но он работает.
		if event.pinned_at and (utils.time_since(event.pinned_at)) < 2:
			return

		# Проверка на то, какой тип сообщения был отредактирован. Если отредактировано было голосовое сообщение, то пропускаем обновление.
		#
		# Понятия не имею почему, но в ВК решили, что при добавлении текста расшифровки голосового сообщения, оно будет редактироваться.
		for i in range(int(event.attachments.get("attachments_count", 0))):
			attachment_type = event.attachments.get(f"attach{i + 1}_type")
			attachment_kind = event.attachments.get(f"attach{i + 1}_kind")

			if attachment_type == "doc" and attachment_kind == "audiomsg":
				return

		logger.debug(f"[VK] Событие редактирования сообщения для подгруппы \"{subgroup.service_dialogue_name}\"")

		# Пытаемся получить ID сообщения в Telegram, которое нужно отредактировать.
		telegram_message = await subgroup.service.get_message_by_service_id(self.service_user_id, event.message_id)

		if not telegram_message:
			return

		# Если это самоуничтожающееся сообщение, которое, ну, самоуничтожилось, то просто удаляем его вместо редактирования.
		if event.is_expired:
			try:
				await subgroup.delete_message(telegram_message.telegram_message_ids)
			except TelegramForbiddenError:
				await TelehooperAPI.delete_group_data(subgroup.parent.chat.id, fully_delete=True, bot=subgroup.parent.bot)
			except Exception:
				pass

			return

		# Подготавливаем текст сообщения, который будет отправлен.
		full_message_text = ""
		msg_prefix = await self.get_message_prefix(event, is_outbox=event.flags.outbox)
		msg_suffix = " <i>(ред.)</i>"

		full_message_text = msg_prefix + utils.telegram_safe_str(event.new_text) + msg_suffix

		# Редактируем сообщение.
		try:
			logger.debug(f"Редактирую сообщение с ID0 {telegram_message.telegram_message_ids[0]}")

			await subgroup.edit_message(
				full_message_text,
				telegram_message.telegram_message_ids[0],
				sender_id=event.from_id if event.from_id != subgroup.service.service_user_id else None
			)
		except TelegramForbiddenError:
			await TelehooperAPI.delete_group_data(subgroup.parent.chat.id, fully_delete=True, bot=subgroup.parent.bot)
		except Exception:
			pass

	async def handle_vk_message_flags_change(self, event: LongpollMessageFlagsEdit) -> None:
		"""
		Обработчик события изменения флагов у уже существующего сообщения во ВКонтакте.

		:param event: Событие типа `LongpollMessageFlagsEdit`, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI

		# Обрабатываем только события удаления сообщения.
		if not (event.new_flags.delete_for_all or event.new_flags.deleted):
			return

		subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(self.user, ServiceDialogue(service_name=self.service_name, id=event.peer_id))

		# Проверяем, что у пользователя есть подгруппа, из которой нужно удалить.
		if not subgroup:
			return

		logger.debug(f"[VK] Событие удаления сообщения с ID {event.message_id} для подгруппы \"{subgroup.service_dialogue_name}\"")

		# Пытаемся получить ID сообщения в Telegram, которое нужно отредактировать.
		telegram_message = await subgroup.service.get_message_by_service_id(self.service_user_id, event.message_id)

		if not telegram_message:
			return

		# Удаляем сообщение.
		try:
			logger.debug(f"Удаляю сообщения с ID {telegram_message.telegram_message_ids}")

			await subgroup.delete_message(
				telegram_message.telegram_message_ids,
				sender_id=subgroup.service.service_user_id if subgroup.service.service_user_id != self.service_user_id else None
			)
		except TelegramForbiddenError:
			await TelehooperAPI.delete_group_data(subgroup.parent.chat.id, fully_delete=True, bot=subgroup.parent.bot)
		except Exception as error:
			if error:
				logger.error(f"Ошибка при удалении сообщения Telegam пользователя {utils.get_telegram_logging_info(self.user.telegramUser)}:", error)

	async def get_list_of_dialogues(self, force_update: bool = False, max_amount: int = 800, skip_ids: list[int] = []) -> list[ServiceDialogue]:
		if not force_update and self._cachedDialogues:
			return self._cachedDialogues

		extendedInfo = {}
		retrieved_dialogues = 0
		total_dialogues = 0
		result = []

		while True:
			response = await self.vkAPI.messages_getConversations(offset=retrieved_dialogues)
			if not total_dialogues:
				total_dialogues = response["count"]

			# ВК очень странно возвращает информацию о списке диалогов,
			# вместо
			#   {информации о диалоге, имя юзера и всё такое}
			# ВК возвращает
			#   {{информация о диалоге}, [{id: имя юзера и всё такое}, ...]}
			#
			# Данный кусок кода немного упрощает это, создавая словарь с информацией.
			for group in response.get("groups", []):
				extendedInfo[-group["id"]] = group

			for user in response.get("profiles", []):
				extendedInfo[user["id"]] = user

			for dialogue in response["items"]:
				convo = dialogue["conversation"]

				conversation_id = convo["peer"]["id"]
				conversation_type = convo["peer"]["type"]
				convo_extended = extendedInfo.get(conversation_id)

				# Про тип "email" можно почитать здесь:
				# https://dev.vk.com/reference/objects/message
				#
				# К сожалению, данный тип бесед имеет отличия от обычных диалогов.
				# Смысла добавлять поддержку такого типа нету, поскольку
				# такие беседы создавать уже не является возможным во ВКонтакте.
				if conversation_type == "email":
					total_dialogues -= 1

					continue

				if conversation_id in skip_ids:
					total_dialogues -= 1

					continue

				full_name = ""
				image_url = "https://vk.com/images/camera_200.png"

				if not convo_extended and conversation_type != "chat":
					raise Exception(f"Не удалось найти расширенную информацию о диалоге {conversation_id}, хотя она обязана быть.")

				if conversation_type == "chat":
					full_name = convo["chat_settings"]["title"]

					if "photo" in convo["chat_settings"]:
						image_url = convo["chat_settings"]["photo"]["photo_200"]
				elif conversation_type == "user":
					convo_extended = cast(dict, convo_extended)

					full_name = f"{convo_extended['first_name']} {convo_extended['last_name']}"
					image_url = convo_extended.get("photo_max")
				elif conversation_type == "group":
					convo_extended = cast(dict, convo_extended)

					full_name = convo_extended["name"]
					image_url = convo_extended.get("photo_max")
				else:
					raise Exception(f"Неизвестный тип диалога {conversation_type}.")

				result.append(
					ServiceDialogue(
						service_name=self.service_name,
						id=conversation_id,
						name=full_name,
						profile_url=image_url,
						is_multiuser=conversation_type == "chat",
						is_pinned=convo["sort_id"]["major_id"] > 0,
						is_muted="push_settings" in convo and convo["push_settings"]["disabled_forever"],
						incoming_messages=convo.get("unread_count", 0),
						multiuser_count=convo["chat_settings"].get("members_count") if conversation_type == "chat" else None
					)
				)

				retrieved_dialogues += 1

			if retrieved_dialogues + 200 >= total_dialogues or retrieved_dialogues + 200 >= max_amount:
				break

		self._cachedDialogues = result
		return result

	def has_cached_list_of_dialogues(self) -> bool:
		return bool(self._cachedDialogues)

	async def disconnect_service(self, reason: ServiceDisconnectReason = ServiceDisconnectReason.INITIATED_BY_USER) -> None:
		db_user = await get_user(self.user.telegramUser)

		assert "VK" in db_user["Connections"]

		try:
			if reason not in [ServiceDisconnectReason.INITIATED_BY_USER, ServiceDisconnectReason.ISSUED_BY_ADMIN]:
				raise Exception

			await self.send_message(
				chat_id=db_user["Connections"]["VK"]["ID"],
				text="ℹ️ Telegram-бот «Telehooper» был отключён от Вашей страницы ВКонтакте."
			)
		except:
			pass

		# Удаляем из БД.
		del db_user["Connections"]["VK"]

		await db_user.save()

		# Удаляем VKServiceAPI из памяти.
		self.user.remove_vk_connection()

		# Отключаем longpoll.
		if self._longPollTask:
			logger.debug("Cancelling longpoll task...")

			self._longPollTask.cancel()

		# Удаляем из памяти.
		try:
			del self.token
			del self.vkAPI
			del self._longPollTask
		except:
			pass

	async def get_current_user_info(self) -> TelehooperServiceUserInfo:
		self_info = await self.vkAPI.get_self_info()

		return TelehooperServiceUserInfo(
			service_name=self.service_name,
			id=self_info["id"],
			name=f"{self_info['first_name']} {self_info['last_name']}",
			profile_url=self_info.get("photo_max_orig"),
		)

	async def get_user_info(self, user_id: int, force_update: bool = False) -> TelehooperServiceUserInfo:
		"""
		Возвращает информацию о пользователе/группе ВКонтакте.

		:param user_id: ID пользователя ВКонтакте.
		:param force_update: Нужно ли обновить информацию о пользователе, если она уже есть в кэше.
		"""

		if not force_update and user_id in self._cachedUsersInfo:
			return self._cachedUsersInfo[user_id]

		# Во ВКонтакте, пользователи имеют положительный ID,
		# пока как группы (т.е., боты) имеют отрицательный.
		#
		# Здесь, в зависимости от знака ID используются разные API-запросы.
		user_info_class: TelehooperServiceUserInfo
		if user_id > 0:
			# Пользователь.

			user_info = (await self.vkAPI.users_get(user_ids=[user_id]))[0]
			assert user_info, f"Данные о пользователе с ID {user_id} не были получены от API ВКонтакте, хотя обязаны были быть"

			user_info_class = TelehooperServiceUserInfo(
				service_name=self.service_name,
				id=user_info["id"],
				name=f"{user_info['first_name']} {user_info['last_name']}",
				profile_url=user_info.get("photo_max_orig"),
				male=user_info.get("sex", 2) == 2, # Судя по документации ВК, может быть и третий вариант с ID 0, "пол не указан". https://dev.vk.com/ru/reference/objects/user#sex
				username=user_info.get("domain", f"id{user_info['id']}")
			)
		else:
			# Группа (бот).

			group_info = (await self.vkAPI.groups_getByID(user_ids=[abs(user_id)]))[0]
			assert group_info, f"Данные о группе с ID {user_id} не были получены от API ВКонтакте, хотя обязаны были быть"

			user_info_class = TelehooperServiceUserInfo(
				service_name=self.service_name,
				id=-group_info["id"],
				name=group_info["name"],
				profile_url=group_info.get("photo_200_orig"),
				male=None,
				username=group_info.get("domain", f"club{group_info['id']}")
			)

		self._cachedUsersInfo[user_id] = user_info_class

		return user_info_class

	async def get_service_dialogue(self, chat_id: int, force_update: bool = False) -> ServiceDialogue:
		dialogues = await self.get_list_of_dialogues(force_update=force_update)

		for dialogue in dialogues:
			if dialogue.id == chat_id:
				return dialogue

		raise TypeError(f"Диалог с ID {chat_id} не найден")

	async def set_online(self) -> None:
		await self.vkAPI.account_setOnline()

	async def start_chat_activity(self, peer_id: int, type: Literal["typing", "audiomessage"] = "typing") -> None:
		await self.vkAPI.messages_setActivity(peer_id=peer_id, type=type)

	async def read_message(self, peer_id: int) -> None:
		await self.vkAPI.messages_markAsRead(peer_id=peer_id)

	async def send_callback(self, message_id: int, peer_id: int, data: str) -> None:
		await self.vkAPI.messages_sendMessageEvent(message_id=message_id, peer_id=peer_id, payload=data)

	async def send_message(self, chat_id: int, text: str, reply_to_message: int | None = None, attachments: list[str] | str | None = None, latitude: float | None = None, longitude: float | None = None, bypass_queue: bool = False) -> int | None:
		if not bypass_queue and not await self.acquire_queue("message"):
			return None

		return await self.vkAPI.messages_send(peer_id=chat_id, message=text, reply_to=reply_to_message, attachment=attachments, lat=latitude, long=longitude)

	async def find_real_chat_id(self, user: "TelehooperUser", subgroup: "TelehooperSubGroup") -> int | None:
		"""
		Возвращает реальный ID беседы в ВКонтакте, если пользователь не является её создателем.

		:param user: Пользователь, для которого нужно найти реальный ID беседы.
		:param subgroup: Подгруппа, для которой нужно найти реальный ID беседы.
		"""

		logger.debug("Сообщение отправил не владелец этой группы, пытаюсь узнать ID группы относительно отправителя...")

		# TODO: Каким-то хитрым образом кэшировать этот ID?
		# TODO: Сделать ещё какую-то проверку, поскольку бот может писать не в ту беседу, если у них совпадает имя.

		for chat in await self.get_list_of_dialogues():
			if not chat.is_multiuser:
				continue

			if chat.name != subgroup.service_dialogue_name:
				continue

			logger.debug(f"Найден реальный ID беседы: {chat.id}")

			return chat.id

		return None

	async def handle_telegram_message(self, msg: Message, subgroup: "TelehooperSubGroup", user: "TelehooperUser", attachments: list[PhotoSize | Video | Audio | TelegramDocument | Voice | Sticker | VideoNote]) -> None:
		from api import TelehooperAPI


		try:
			message_text = msg.text or msg.caption or ""

			logger.debug(f"[TG] Обработка сообщения в Telegram: \"{message_text}\" в \"{subgroup}\" {'с вложениями' if attachments else ''}")

			# Если это сервисное сообщение об удалении (кика) бота из группы, то обрабатываем это.
			if msg.left_chat_member and msg.left_chat_member.id == subgroup.parent.bot.id:
				await TelehooperAPI.delete_group_data(subgroup.parent.chat.id, fully_delete=True, bot=subgroup.parent.bot)

				return

			# Получаем ID беседы. Используется, если отправитель сообщения - не владелец группы.
			peer_id = subgroup.service_chat_id
			is_multiuser_chat = peer_id > 2000000000
			sent_by_owner = True

			if subgroup.parent.creatorID != user.telegramUser.id:
				peer_id = await self.find_real_chat_id(user, subgroup)
				sent_by_owner = False

				if not peer_id:
					return

			# Обрабатываем "ответы" на сообщение.
			reply_message_id = None
			if msg.reply_to_message and msg.reply_to_message.from_user:
				service_user_id = self.service_user_id
				saved_message = None

				# Если мы находимся в беседе, нужно найти ID сообщения пользователя во ВКонакте, на сообщение которого сделали reply.
				# Мы ищем такого пользователя лишь в случае, если пользователь сделал ответ на сообщение другого реального пользователя, а не бота.
				if is_multiuser_chat and not sent_by_owner:
					telegram_user_id = subgroup.parent.creatorID

					if msg.reply_to_message.from_user.id != subgroup.parent.bot.id:
						# Сообщение в реплае было отправлено реальным пользователем либо миниботом. Нужно определить, кем именно оно было отправлено.
						if msg.reply_to_message.from_user.username in subgroup.parent.associatedMinibots.values():
							# Это минибот, значит извлекаем Telegram User ID, который ассоциирован с данным миниботом.
							# Проблема, однако, в том, что миниботы могут быть присвоены к нескольким пользователям сразу.
							# Ввиду этого, реплаи пока что не работают :(

							pass
						else:
							# Сообщение в реплае было отправлено реальным пользователем. Значит ищем относительно ID этого пользователя.
							telegram_user_id = msg.reply_to_message.from_user.id

					for serviceAPI in TelehooperAPI.get_service_apis():
						if serviceAPI.service_name != self.service_name:
							continue

						if serviceAPI.user.telegramUser.id != telegram_user_id:
							continue

						service_user_id = serviceAPI.service_user_id
						logger.debug(f"ID пользователя во ВКонтакте, на сообщение которого сделали reply {service_user_id}")

				saved_message = await self.get_message_by_telegram_id(service_user_id, msg.reply_to_message.message_id)

				# Если мы находимся в беседе, то ID сообщения, на который был сделан ответ,
				# может быть неправильный, если реплай был сделан на сообщение от другого пользователя.
				#
				# Благодаря тому, что бот хранит ConversationMID'ы, мы можем найти "реальный" ID относительно
				# текущего пользователя, что написал сообщение.
				if is_multiuser_chat and not sent_by_owner and saved_message and saved_message.service_conversation_message_ids:
					reply_message_info = await self.vkAPI.messages_getByConversationMessageId(peer_id, saved_message.service_conversation_message_ids[0])
					if reply_message_info["items"]:
						reply_message_id = reply_message_info["items"][0]["id"]
				else:
					reply_message_id = saved_message.service_message_ids[0] if saved_message else None

			attachments_to_send: str | None = None
			if attachments:
				attachments_vk = cast(PhotoSize | Video | Audio | TelegramDocument | Voice | Sticker | VideoNote | str, attachments.copy())

				for attch_type in ["PhotoSize", "Video", "Audio", "Document", "Voice", "Sticker", "VideoNote"]:
					allow_multiple_uploads = attch_type != "Document"
					multiple_uploads_amount = 5 if allow_multiple_uploads else 1

					attchs_of_same_type = [attch for attch in attachments_vk if attch.__class__.__name__ == attch_type]

					if not attchs_of_same_type:
						continue

					# "Готовое" значение вложения. Если тут есть значение, то мы не должны по-новой загружать вложение.
					attachment_value: str | None = None

					# По 5 элементов.
					attachments_results: list[dict] = []
					attachments_telegram_docs: list[TelegramDocument] = []
					filenames: list[str] = []
					for index in range(0, len(attchs_of_same_type), multiple_uploads_amount):
						attchs_of_same_type_part = attchs_of_same_type[index:index + multiple_uploads_amount]

						upload_url: str | None = None
						ext: str | None = None
						if attch_type == "PhotoSize":
							upload_url = (await self.vkAPI.photos_getMessagesUploadServer(peer_id=peer_id))["upload_url"]
							ext = "jpg"
						elif attch_type == "Voice":
							assert len(attachments) == 1, "Вложение типа Voice не может быть отправлено вместе с другими вложениями"

							upload_url = (await self.vkAPI.docs_getMessagesUploadServer(type="audio_message", peer_id=peer_id))["upload_url"]
							ext = "ogg"
						elif attch_type in ["Video", "VideoNote"]:
							upload_url = (await self.vkAPI.video_save(name="Video message", is_private=True, wallpost=False))["upload_url"]
							ext = "mp4"
						elif attch_type == "Sticker":
							assert len(attachments) == 1, "Вложение типа Sticker не может быть отправлено вместе с другими вложениями"

							# Проверяем в кэше.
							sticker_cache_name = f"sticker{attachments[0].file_unique_id}static"
							attachment_value = await TelehooperAPI.get_attachment("VK", sticker_cache_name)

							if not attachment_value:
								upload_url = (await self.vkAPI.docs_getMessagesUploadServer(type="graffiti", peer_id=peer_id))["upload_url"]
								ext = "png"
						elif attch_type == "Document":
							# Проверяем в кэше.
							document_cache_name = f"gif{attachments[0].file_unique_id}"
							attachment_value = await TelehooperAPI.get_attachment("VK", document_cache_name)

							if not attachment_value:
								upload_url = (await self.vkAPI.docs_getMessagesUploadServer(type="doc", peer_id=peer_id))["upload_url"]

								for file_same_type in attchs_of_same_type_part:
									filenames.append(cast(TelegramDocument, file_same_type).file_name or "unknown-filename.txt")
						elif attch_type == "Audio":
							error_message = await msg.reply(
								"<b>⚠️ Ошибка пересылки сообщения</b>.\n"
								"\n"
								"Музыка не поддерживается при пересылке во ВКонтакте.",
								allow_sending_without_reply=True
							)

							# Удаляем сообщение об ошибке через время.
							await asyncio.sleep(60)
							try:
								await error_message.delete()
							except:
								pass

							return
						else:
							raise TypeError(f"Неизвестный тип вложения {attch_type}")

						logger.debug(f"URL для загрузки вложений типа {attch_type}: {upload_url}")

						# Выгружаем вложения на сервера ВК.
						if upload_url:
							assert ext or attch_type == "Document", f"Не дано расширение для вложения типа {attch_type}"

							async with aiohttp.ClientSession() as client:
								form_data = aiohttp.FormData()

								async def _download(index, file_id: str) -> tuple[int, bytes]:
									logger.debug(f"Загружаю вложение #{index} из Telegram с FileID {file_id}")

									file = await subgroup.parent.bot.download(file_id)
									assert file, "Не удалось загрузить вложение из Telegram"

									return index, file.read()

								# Подготавливаем список задач на загрузку вложений.
								tasks = []
								for index, attach in enumerate(attchs_of_same_type_part):
									attach = cast(PhotoSize | Audio | TelegramDocument | Video | Voice, attach)

									tasks.append(_download(index, attach.file_id))

								# Ожидаем загрузки, восстанавливаем преждний порядок.
								downloaded_results = await asyncio.gather(*tasks)
								downloaded_results.sort(key=lambda x: x[0])

								for index, file_bytes in downloaded_results:
									# ВКонтакте отправляет незадокументированную ошибку "no_file", если при отправке
									# документов (в т.ч. и голосовых сообщений) в FormData используется поле "file1" вместо "file".
									field_name = "file"
									if len(attchs_of_same_type_part) > 1:
										field_name = f"file{index}"

									# Если нам дан стикер, то изменяем его размера.
									if attch_type == "Sticker":
										try:
											file_bytes = await prepare_sticker(file_bytes)
										except PIL.UnidentifiedImageError as error:
											error_message = await msg.reply(
												"<b>⚠️ Ошибка пересылки сообщения</b>.\n"
												"\n"
												"Анимированные стикеры не поддерживаются.",
												allow_sending_without_reply=True
											)

											# Удаляем сообщение об ошибке через время.
											await asyncio.sleep(60)
											try:
												await error_message.delete()
											except:
												pass

											return

									# Если нам дан документ, который является видео, то мы должны превратить его в gif.
									this_attach = attchs_of_same_type_part[index]
									if len(attchs_of_same_type_part) == 1 and isinstance(this_attach, TelegramDocument) and this_attach.mime_type == "video/mp4":
										try:
											file_bytes = await utils.convert_mp4_to_gif(file_bytes)
										except Exception as error:
											raise Exception(f"Ошибка при конвертации mp4 из Telegram как gif")

									form_data.add_field(name=field_name, value=file_bytes, filename=f"file{index}.{ext}" if ext else filenames.pop(0))

								# Отправляем загруженные вложения на сервера ВК.
								async with client.post(upload_url, data=form_data) as response:
									assert response.status == 200, f"Не удалось загрузить вложение типа {attch_type}"
									response = VKAPI._parse_response(await response.json(content_type=None), "_get.server_")

									attachments_results.append(response)
									attachments_telegram_docs.append(attchs_of_same_type_part[index]) # type: ignore

					# Закончили отправлять все вложения пачками по 5 элементов.
					# Говорим ВК, что мы хотим отправить вложения в сообщении.
					attachment_str_list: list[str] = []

					# Если мы уже извлекли вложение из кэша, то нам нужно просто их добавить в список.
					if attachment_value:
						attachment_str_list.append(attachment_value)
					else:
						for index, attachment in enumerate(attachments_results):
							telegram_document = attachments_telegram_docs[index]

							if attch_type == "PhotoSize":
								assert attachment["photo"], "Объект photo является пустым"
								resp = await self.vkAPI.photos_saveMessagesPhoto(photo=attachment["photo"], server=attachment["server"], hash=attachment["hash"])

								for saved_attch in resp:
									attachment_str_list.append(get_attachment_key(saved_attch, type="photo"))
							elif attch_type == "Voice":
								saved_attch = (await self.vkAPI.docs_save(file=attachment["file"], title="Voice message"))["audio_message"]

								attachment_str_list.append(get_attachment_key(saved_attch, type="doc"))
							elif attch_type in ["Video", "VideoNote"]:
								attachment_str_list.append(get_attachment_key(attachment, type="video"))
							elif attch_type == "Sticker":
								saved_attch = (await self.vkAPI.docs_save(file=attachment["file"], title="Sticker"))["graffiti"]

								attachment_str = get_attachment_key(saved_attch, type="doc")
								attachment_str_list.append(attachment_str)

								# Стикеры нам нужно кэшировать, если пользователь это разрешил.
								if await self.user.get_setting("Security.MediaCache"):
									await TelehooperAPI.save_attachment(
										"VK",
										f"sticker{telegram_document.file_unique_id}static",
										attachment_str
									)
							elif attch_type == "Document":
								saved_attch = (await self.vkAPI.docs_save(file=attachment["file"]))["doc"]

								attachment_str = get_attachment_key(saved_attch, type="doc")
								attachment_str_list.append(attachment_str)

								# Если у нас гифка, и пользователь разрешил кэширование, то кэшируем.
								if isinstance(telegram_document, TelegramDocument) and telegram_document.mime_type == "video/mp4" and await self.user.get_setting("Security.MediaCache"):
									await TelehooperAPI.save_attachment(
										"VK",
										f"gif{telegram_document.file_unique_id}",
										attachment_str
									)

					# Теперь нам нужно заменить вложения в сообщении на те, что мы получили от ВК.
					for index, attch in enumerate(attachments_vk):
						if attch.__class__.__name__ != attch_type:
							continue

						attachments_vk[index] = attachment_str_list.pop(0) # type: ignore

				# Мы закончили работать с вложениями! Проверяем, что мы обработали все вложения.
				assert all(isinstance(attch, str) for attch in attachments_vk), "Не все вложения были обработаны"

				attachments_to_send = ",".join(cast(list[str], attachments_vk))

				logger.debug(f"Вложения для отправки: {attachments_to_send}")

			# Если у нас нет вложений, а так же нет текста сообщения, то мы не можем отправить сообщение.
			if not attachments_to_send and not message_text:
				return

			# Перед отправкой, мы сохраняем текст сообщения, дабы бот знал, что сообщение было и вправду отправлено через бота.
			# Пояснение: Иногда, longpoll возвращает событие о новом сообщении раньше, чем messages.send возвращает ID отправленного сообщения.
			subgroup.pre_message_cache[message_text.lower().strip()] = None

			# Если разрешено, то устанавливаем статус "онлайн".
			# Перед запросом проверяется, что с момента обновления онлайна ботом прошло как минимум 60 секунд.
			if utils.time_since(self._lastOnlineStatus) > 60 and self.get_bucket_size("message") < 5 and await self.user.get_setting("Services.VK.SetOnline"):
				self._lastOnlineStatus = utils.get_timestamp()

				await self.set_online()

			# Отправляем сообщение.
			vk_message_id = await self.send_message(
				chat_id=peer_id,
				text=message_text,
				reply_to_message=reply_message_id,
				attachments=attachments_to_send,
				latitude=msg.location.latitude if msg.location else None,
				longitude=msg.location.longitude if msg.location else None
			)

			# В некоторых случаях сообщение может быть не отправлено из-за большой очереди.
			if not vk_message_id:
				return

			# Если сообщение было отправлено в беседу, то мы можем получить ConversationMID для хранения в памяти.
			conversation_mid = None
			if is_multiuser_chat:
				try:
					message_data = await self.vkAPI.messages_getById(vk_message_id)
					if message_data and message_data["items"]:
						message_data = message_data["items"][0]

					conversation_mid = message_data["conversation_message_id"]
				except:
					pass

			# Сохраняем ID сообщения.
			await TelehooperAPI.save_message(
				"VK",
				self.service_user_id,
				msg.message_id,
				vk_message_id,
				conversation_mid,
				sent_via_bot=True
			)
		except TooManyRequestsException:
			await msg.reply(
				"<b>⚠️ Вы отправляете сообщения слишком быстро</b>.\n"
				"\n"
				"Сервера ВКонтакте передали ошибку о том, что Вы отправляете слишком часто. Пожалуйста, старайтесь отправлять сообщения реже.\n"
				"\n"
				"ℹ️ Отправленное Вами сообщение в Telegram, вероятнее всего, будет пропущено из-за этой ошибки.",
				allow_sending_without_reply=True
			)
		except Exception as error:
			logger.exception(f"[TG] Ошибка при пересылке Telegram-сообщения во ВКонтакте от пользователя {utils.get_telegram_logging_info(msg.from_user)}:", error)

			await msg.reply(
				"<b>⚠️ Ошибка при отправке сообщения</b>.\n"
				"\n"
				"<i><b>Упс!</b></i> Что-то пошло не так, и бот столкнулся с ошибкой при попытке переслать сообщение во ВКонтакте. 😓\n"
				"Отправленное Вами сообщение не будет отправлено во ВКонтакте.\n"
				"\n"
				"<b>Текст ошибки, если Вас попросили его отправить</b>:\n"
				f"<code>{error.__class__.__name__}: {error}</code>.\n"
				"\n"
				f"ℹ️ Пожалуйста, подождите, перед тем как попробовать снова. Если проблема не проходит через время - попробуйте попросить помощи либо создать баг-репорт (Github Issue), по ссылке в команде <a href=\"{utils.create_command_url('/h 6')}\">/help</a>.",
				allow_sending_without_reply=True
			)

		# Сохраняем последнее время взаимодействия с сервисом.
		await self.update_last_activity()

	async def handle_telegram_message_delete(self, msg: Message, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		from api import TelehooperAPI


		logger.debug(f"[TG] Обработка удаления сообщения в Telegram: \"{msg.text}\" в \"{subgroup}\"")

		saved_message = await self.get_message_by_telegram_id(self.service_user_id, msg.message_id)

		if not saved_message:
			error_message = await subgroup.send_message_in(
				"<b>⚠️ Ошибка удаления сообщения</b>.\n"
				"\n"
				"Сообщение не было найдено ботом, поэтому оно не было удалено.",
				silent=True
			)

			# Удаляем сообщение об ошибке через время.
			if error_message:
				await asyncio.sleep(60)
				try:
					await subgroup.delete_message(error_message)
				except:
					pass

			return

		try:
			await self.vkAPI.messages_delete(saved_message.service_message_ids)
		except AccessDeniedException:
			# TODO: Уточнить причину ошибки в зависимости от типа диалога.

			reason = "Прошло более 24-х часов с момента отправки сообщения."
			if not saved_message.sent_via_bot:
				reason = "Вы попытались удалить сообщение, отправленное Вашим собедеседником, либо же Вы не являетесь Администратором в беседе."

			error_message = await subgroup.send_message_in(
				"<b>⚠️ Ошибка удаления сообщения</b>.\n"
				"\n"
				f"{reason}",
				silent=True
			)

			# Удаляем сообщение об ошибке через время.
			if error_message:
				await asyncio.sleep(60)
				try:
					await subgroup.delete_message(error_message)
				except:
					pass

			return

		# Удаляем из кэша сообщений.
		await TelehooperAPI.delete_message(
			"VK",
			saved_message.service_message_ids
		)

	async def handle_telegram_message_edit(self, msg: Message, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		logger.debug(f"[TG] Обработка редактирования сообщения в Telegram: \"{msg.text}\" в \"{subgroup}\"")

		saved_message = await self.get_message_by_telegram_id(self.service_user_id, msg.message_id)

		if not saved_message:
			error_message = await subgroup.send_message_in(
				"<b>⚠️ Ошибка редактирования сообщения</b>.\n"
				"\n"
				"Сообщение не было найдено ботом, поэтому оно не было отредактировано.",
				silent=True,
				reply_to=msg.message_id
			)

			# Удаляем сообщение об ошибке через время.
			if error_message:
				await asyncio.sleep(60)
				try:
					await subgroup.delete_message(error_message)
				except:
					pass

			return

		# Получаем ID беседы. Используется, если тот, кто отредактировал сообщение - не владелец группы.
		peer_id = subgroup.service_chat_id
		sent_by_owner = True

		if subgroup.parent.creatorID != user.telegramUser.id:
			peer_id = await self.find_real_chat_id(user, subgroup)
			sent_by_owner = False

			if not peer_id:
				return

		try:
			await self.vkAPI.messages_edit(
				message_id=saved_message.service_message_ids[0],
				peer_id=peer_id,
				message=msg.text or "[пустой текст сообщения]"
			)
		except AccessDeniedException:
			error_message = await subgroup.send_message_in(
				"<b>⚠️ Ошибка редактирования сообщения</b>.\n"
				"\n"
				f"Сообщение слишком старое что бы его редактировать.",
				silent=True
			)

			# Удаляем сообщение об ошибке через время.
			if error_message:
				await asyncio.sleep(60)
				try:
					await subgroup.delete_message(error_message)
				except:
					pass

	async def handle_telegram_message_read(self, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		logger.debug(f"[TG] Обработка прочтения сообщения в Telegram в \"{subgroup}\"")

		# Получаем ID беседы. Используется, если тот, кто прочитал сообщение - не владелец группы.
		peer_id = subgroup.service_chat_id
		sent_by_owner = True

		if subgroup.parent.creatorID != user.telegramUser.id:
			peer_id = await self.find_real_chat_id(user, subgroup)
			sent_by_owner = False

			if not peer_id:
				return

		await self.read_message(peer_id)

	async def handle_telegram_callback_button(self, query: CallbackQuery, subgroup: "TelehooperSubGroup", user: "TelehooperUser") -> None:
		from api import TelehooperAPI

		assert query.data, "Не были переданы данные Callback query"
		assert query.message, "Не были переданы кнопка для Callback query"

		logger.debug(f"[TG] Обработка Inline callback query сервиса в Telegram в \"{subgroup}\"")

		# Получаем информацию о сообщении, в котором находится эта кнопка.
		saved_message = await self.get_message_by_telegram_id(self.service_user_id, query.message.message_id)

		# Пытаемся получить информацию о Inline callback query для сервиса.
		service_callback_query = subgroup.get_callback_btn(query.data)

		# Если такая кнопка не была найдена, то вызываем ошибку.
		if not (saved_message and service_callback_query):
			await query.answer(
				"⚠️ Данные устарели.\n"
				"\n"
				"ℹ️ Попробуйте отправить сообщение с этой кнопкой ещё раз и попробуйте снова.",
				show_alert=True
			)

			return

		# Получаем ID беседы. Используется, если тот, кто отредактировал сообщение - не владелец группы.
		peer_id = subgroup.service_chat_id
		sent_by_owner = True

		if subgroup.parent.creatorID != user.telegramUser.id:
			peer_id = await self.find_real_chat_id(user, subgroup)
			sent_by_owner = False

			if not peer_id:
				return

		await self.send_callback(saved_message.service_message_ids[0], peer_id, service_callback_query)

	async def get_message_by_telegram_id(self, service_owner_id: int, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		from api import TelehooperAPI

		return await TelehooperAPI.get_message_by_telegram_id("VK", message_id, service_owner_id, bypass_cache=bypass_cache)

	async def get_message_by_service_id(self, service_owner_id: int, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		from api import TelehooperAPI

		return await TelehooperAPI.get_message_by_service_id("VK", message_id, service_owner_id, bypass_cache=bypass_cache)

	@staticmethod
	async def reconnect_on_restart(user: "TelehooperUser", db_user: Document, bot: Bot) -> Optional["VKServiceAPI"]:
		vkServiceAPI = None

		# Проверка, что токен установлен.
		# Токен может отсутствовать, если настройка Security.StoreTokens была выставлена в значение «выключено».
		if not db_user["Connections"]["VK"]["Token"]:
			db_user["Connections"].pop("VK")
			await db_user.save()

			# Отправляем сообщение.
			await bot.send_message(
				chat_id=db_user["ID"],
				text=utils.replace_placeholders(
					"<b>⚠️ Потеряно соединение с ВКонтакте</b>.\n"
					"\n"
					"Telehooper потерял соединение со страницей «ВКонтакте», поскольку настройка {{Security.StoreTokens}} была выставлена в значение «выключено».\n"
					"\n"
					"ℹ️ Вы можете повторно подключиться к «ВКонтакте», используя команду /connect.\n"
				)
			)

			return

		# Создаём Longpoll.
		try:
			vkServiceAPI = VKServiceAPI(
				token=SecretStr(utils.decrypt_with_env_key(db_user["Connections"]["VK"]["Token"])),
				vk_user_id=db_user["Connections"]["VK"]["ID"],
				user=user
			)
			user.save_connection(vkServiceAPI)

			# Запускаем Longpoll.
			await vkServiceAPI.start_listening(bot)

			# Возвращаем ServiceAPI.
			return vkServiceAPI
		except Exception as error:
			logger.exception(f"Не удалось запустить LongPoll для пользователя {utils.get_telegram_logging_info(user.telegramUser)}:", error)

			# В некоторых случаях, сам объект VKServiceAPI может быть None,
			# например, если не удалось расшифровать токен.
			# В таких случаях нам необходимо сделать отключение, при помощи
			# фейкового объекта VKServiceAPI.
			if vkServiceAPI is None:
				vkServiceAPI = VKServiceAPI(
					token=None, # type: ignore
					vk_user_id=db_user["Connections"]["VK"]["ID"],
					user=user
				)

			# Совершаем отключение.
			await vkServiceAPI.disconnect_service(ServiceDisconnectReason.ERRORED)

			# Отправляем сообщение.
			await bot.send_message(
				chat_id=db_user["ID"],
				text=(
					"<b>⚠️ Произошла ошибка при работе с ВКонтакте</b>.\n"
					"\n"
					"К сожалению, ввиду ошибки бота, у Telehooper не удалось востановить соединение с Вашей страницей «ВКонтакте».\n"
					"Вы не сможете отправлять или получать сообщения из этого сервиса до тех пор, пока Вы не переподключитесь к нему.\n"
					"\n"
					"ℹ️ Вы можете повторно подключиться к сервису «ВКонтакте», используя команду /connect.\n"
				)
			)

	async def update_last_activity(self) -> None:
		await self.user.refresh_document()

		self.user.document["Connections"]["VK"]["LastActivityAt"] = utils.get_timestamp()

		# В некоторых случаях случается конфликт.
		# Такая ошибка не очень страшна в данном контексте, поэтому тихо игнорируем её.
		try:
			await self.user.document.save()
		except:
			pass

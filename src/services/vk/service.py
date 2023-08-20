# coding: utf-8

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal, Optional, cast

import aiohttp
from aiocouch import Document
from aiogram import Bot
from aiogram.types import Audio, BufferedInputFile
from aiogram.types import Document as TelegramDocument
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           InputMediaAudio, InputMediaDocument,
                           InputMediaPhoto, InputMediaVideo, Location, Message,
                           PhotoSize, Sticker, Video, VideoNote, Voice)
from aiogram.utils.chat_action import ChatActionSender
import cachetools
from loguru import logger
from pydantic import SecretStr

import utils
from config import config
from DB import get_user
from services.service_api_base import (BaseTelehooperServiceAPI,
                                       ServiceDialogue,
                                       ServiceDisconnectReason,
                                       TelehooperServiceUserInfo)
from services.vk.exceptions import AccessDeniedException, TokenRevokedException
from services.vk.utils import create_message_link
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
	_lastOnlineStatus: int = 0
	"""UNIX-timestamp последнего обновления статуса онлайна через бота. Используется для настройки `Security.StoreTokens`."""
	_cachedUsersInfo: cachetools.TLRUCache[int, TelehooperServiceUserInfo] = cachetools.TLRUCache(maxsize=80, ttu=lambda _, value, now: now + 5 * 60)  # 80 элементов, 5 минут хранения.
	"""Кэшированные данные о пользователях ВКонтакте для быстрого повторного получения."""

	def __init__(self, token: SecretStr, vk_user_id: int, user: "TelehooperUser") -> None:
		super().__init__("VK", vk_user_id, user)

		self.token = token
		self.user = user

		self.vkAPI = VKAPI(self.token)

	async def start_listening(self, bot: Bot | None = None) -> asyncio.Task:
		async def handle_updates() -> None:
			try:
				longpoll = VKAPILongpoll(self.vkAPI, user_id=self.service_user_id)

				async for event in longpoll.listen_for_updates():
					await self.handle_update(event)
			except TokenRevokedException as e:
				# Отправляем сообщение, если у нас есть объект бота.
				if bot:
					try:
						await bot.send_message(
							chat_id=self.user.telegramUser.id,
							text=(
								"<b>⚠️ Потеряно соединение с ВКонтакте</b>.\n"
								"\n"
								f"Telehooper потерял соединение со страницей «ВКонтакте», поскольку владелец страницы отозвал доступ к ней через настройки «Приватности» страницы.\n"
								"\n"
								"ℹ️ Вы можете повторно подключиться к «ВКонтакте», используя команду /connect.\n"
							)
						)
					except:
						pass

				# Совершаем отключение.
				await self.disconnect_service(ServiceDisconnectReason.ERRORED)
			except Exception as e:
				logger.exception(f"Глобальная ошибка (start_listening) обновления ВКонтакте, со связанным Telegram-пользователем {utils.get_telegram_logging_info(self.user.telegramUser)}:", e)

		self._longPollTask = asyncio.create_task(handle_updates())
		return self._longPollTask

	async def handle_update(self, event: BaseVKLongpollEvent) -> None:
		"""
		Метод, обрабатывающий события VK Longpoll.

		:param event: Событие, полученное с longpoll-сервера.
		"""

		logger.debug(f"[VK] Новое событие {event.__class__.__name__}: {event.event_data}")

		if type(event) is LongpollNewMessageEvent:
			await self.handle_new_message(event)
		elif type(event) is LongpollTypingEvent or type(event) is LongpollTypingEventMultiple or type(event) is LongpollVoiceMessageEvent:
			await self.handle_typing(event)
		elif type(event) is LongpollMessageEditEvent:
			await self.handle_edit(event)
		elif type(event) is LongpollMessageFlagsEdit:
			await self.handle_message_flags_change(event)
		else:
			logger.warning(f"[VK] Метод handle_update столкнулся с неизвестным событием {event.__class__.__name__}: {event.event_data}")

	async def handle_new_message(self, event: LongpollNewMessageEvent) -> None:
		"""
		Обработчик полученных новых сообщений во ВКонтакте.

		:param event: Событие типа `LongpollNewMessageEvent`, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(self.user, ServiceDialogue(service_name=self.service_name, id=event.peer_id))

		# Проверяем, что у пользователя есть подгруппа, в которую можно отправить сообщение.
		if not subgroup:
			return

		logger.debug(f"[VK] Сообщение с текстом \"{event.text}\", для подгруппы \"{subgroup.service_dialogue_name}\"")

		# Обновляем объект пользователя.
		await self.user.refresh_document()

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
			from_self = (not is_convo and is_outbox) or (is_convo and event.from_id and event.from_id == self.service_user_id)

			# Проверяем, стоит ли боту обрабатывать исходящие сообщения.
			if is_outbox and not (ignore_outbox_debug or await self.user.get_setting("Services.VK.ViaServiceMessages")):
				return

			# Получаем информацию о отправленном сообщении.
			#
			# Небольшая задержка здесь нужна, потому что бот может получить сообщение раньше, чем оно будет сохранено в БД.
			# Асинхронность - это весело! 🤡
			await asyncio.sleep(0.05)
			msg_saved = await subgroup.service.get_message_by_service_id(event.message_id)

			# Проверяем, не было ли отправлено сообщение самим ботом.
			sent_via_bot = msg_saved and msg_saved.sent_via_bot
			if sent_via_bot and not ignore_outbox_debug:
				return

			# Проверяем, не было ли это событие беседы из ВК.
			if is_convo and event.source_act:
				# Здесь мы не сохраняем ID сообщения, поскольку с таковыми в любом случае нельзя взаимодействовать.
				# TODO: Сделать настройку, что бы бот синхронизировал изменения.

				issuer_name_with_link = None
				victim_name_with_link = None

				if event.from_id:
					issuer_info = await self.get_user_info(event.from_id)

					issuer_name_with_link = f"<a href=\"{'m.' if use_mobile_vk else ''}vk.com/id{event.from_id}\">{utils.compact_name(issuer_info.name) if use_compact_names else issuer_info.name}</a>"

				if event.source_mid:
					victim_info = await self.get_user_info(event.source_mid)

					victim_name_with_link = f"<a href=\"{'m.' if use_mobile_vk else ''}vk.com/id{event.source_mid}\">{utils.compact_name(victim_info.name) if use_compact_names else victim_info.name}</a>"

				messages = {
					"chat_photo_update": f"Пользователь <b>{issuer_name_with_link}</b> <b>обновил(-а)</b> фотографию беседы",
					"chat_photo_remove": f"Пользователь <b>{issuer_name_with_link}</b> <b>удалил(-а)</b> фотографию беседы",
					"chat_create": f"Пользователь <b>{issuer_name_with_link}</b> создал(-а) <b>новую беседу</b>: <b>«{event.source_text}»</b>",
					"chat_title_update": f"Пользователь <b>{issuer_name_with_link}</b> <b>изменил(-а)</b> имя беседы на <b>«{event.source_text}»</b>",
					"chat_invite_user": f"Пользователь <b>{issuer_name_with_link}</b> <b>добавил(-а)</b> пользователя <b>{victim_name_with_link}</b>",
					"chat_kick_user": f"Пользователь <b>{issuer_name_with_link}</b> <b>удалил(-а)</b> пользователя <b>{victim_name_with_link}</b> из беседы",
					"chat_invite_user_by_link": f"Пользователь <b>{victim_name_with_link}</b> <b>присоеденился(-ась)</b> к беседе используя <b>пригласительную ссылку</b>",
					"chat_invite_user_by_message_request": f"Пользователь <b>{victim_name_with_link}</b> <b>присоденился(-ась)</b> к беседе используя <b>запрос на вступление</b>",
					"chat_pin_message": f"Пользователь <b>{issuer_name_with_link}</b> <b>закрепил(-а)</b> сообщение",
					"chat_unpin_message": f"Пользователь <b>{issuer_name_with_link}</b> <b>открепил(-а)</b> закреплённое сообщение",
					"chat_screenshot": f"Пользователь <b>{victim_name_with_link}</b> сделал(-а) <b>скриншот чата</b>",
					"conversation_style_update": f"Пользователь <b>{issuer_name_with_link}</b> <b>обновил</b> стиль чата"
					# "call_ended": f"Пользователь <b>{victim_name_with_link}</b> начал(-а) <b>вызов ВКонтакте</b>. Присоедениться можно <a href=\"https://vk.com/call/join/{group_chat_join_link}\">по ссылке</a>"
				}
				message = messages.get(event.source_act)

				if not message:
					logger.warning(f"[VK] Неизвестное событие беседы: {event.source_act}")

					message = f"Неизвестное действие: <code>«{event.source_act}»</code>"

					return

				await subgroup.send_message_in(f"ℹ️  {message}  ℹ️", disable_web_preview=True)

				return

			# Получаем ID сообщения с ответом, а так же парсим вложения сообщения.
			reply_to = None

			# Парсим вложения.
			if event.attachments or is_group:
				attachments = event.attachments.copy()

				# Добываем полную информацию о сообщении.
				message_extended = (await self.vkAPI.messages_getById(event.message_id))["items"][0]

				# Обрабатываем ответы (reply).
				if "reply" in attachments or ("fwd_messages" in message_extended and len(message_extended["fwd_messages"]) == 1 and await self.user.get_setting("Services.VK.FWDAsReply")):
					reply_vk_message_id = message_extended["reply_message"]["id"] if "reply" in attachments else message_extended["fwd_messages"][0]["id"]

					# Настоящий ID сообщения, на которое был дан ответ, получен. Получаем информацию о сообщении с БД бота.
					telegram_message = await subgroup.service.get_message_by_service_id(reply_vk_message_id)

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

							if button_type == "text":
								current_row.append(InlineKeyboardButton(text=button["action"]["label"], callback_data=button["action"]["payload"] or "do-nothing"))
							else:
								logger.warning(f"[VK] Неизвестный тип action для кнопки: \"{button_type}\"")

								current_row.append(InlineKeyboardButton(text=f"❔ Кнопка типа {button_type}", callback_data=button["action"]["payload"] or "do-nothing"))

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
						reply_to=reply_to
					)

					# Если произошёл rate limit, то msg будет None.
					if not msg:
						return

					await TelehooperAPI.save_message(
						"VK",
						msg[0].message_id,
						event.message_id,
						False
					)

					return

				# Проходимся по всем вложениям.
				if message_extended and "attachments" in message_extended:
					for attch_index, attachment in enumerate(message_extended["attachments"]):
						attachment_type = attachment["type"]
						attachment = attachment[attachment["type"]]

						if attachment_type == "photo":
							attachment_media.append(InputMediaPhoto(type="photo", media=attachment["sizes"][-1]["url"]))
						elif attachment_type == "video":
							# Так как ВК не выдают прямую ссылку на видео, необходимо её извлечь из API.
							# Что важно, передать ссылку напрямую не получается, поскольку ВК проверяет
							# UserAgent и IP адрес, с которого был сделан запрос.

							# Проверяем, видеосообщение (кружочек) ли это?
							is_video_note = attachments.get(f"attach{attch_index + 1}_kind") == "video_message"

							async with ChatActionSender(chat_id=subgroup.parent.chat.id, action="upload_video", bot=subgroup.parent.bot):
								video = (await self.vkAPI.video_get(videos=f"{attachment['owner_id']}_{attachment['id']}_{attachment['access_key']}"))["items"][0]["files"]

								video_quality_list = ["mp4_720", "mp4_480", "mp4_360", "mp4_240", "mp4_144"]

								# Если пользователь разрешил использование видео в 1080p, то добавляем его в список.
								if await self.user.get_setting("Services.VK.HDVideo"):
									video_quality_list.insert(0, "mp4_1080")

								for quality in video_quality_list:
									is_last = quality == "mp4_144"

									if quality not in video:
										continue

									logger.debug(f"Найдено видео с качеством {quality}: {video[quality]}")

									# Загружаем видео.
									async with aiohttp.ClientSession() as client:
										async with client.get(video[quality]) as response:
											assert response.status == 200, f"Не удалось загрузить видео с качеством {quality}"

											video_bytes = b""

											while True:
												chunk = await response.content.read(1024)
												if not chunk:
													break

												video_bytes += chunk

												# Пытаемся найти самое большое видео, которое не превышает 50 МБ.
												if len(video_bytes) > 50 * 1024 * 1024:
													if is_last:
														raise Exception("Размер видео слишком большой")

													logger.debug(f"Файл размером {quality} оказался слишком большой ({len(video_bytes)} байт).")

													continue

									# Если мы получили видеосообщение (кружочек), то нужно отправить его как сообщение.
									if is_video_note:
										# Отправляем видеосообщение.
										msg = await subgroup.send_video_note(
											input=BufferedInputFile(video_bytes, filename=f"VK video note {attachment['id']}.mp4"),
											silent=is_outbox,
											reply_to=reply_to
										)

										# Если произошёл rate limit, то msg будет None.
										if not msg:
											return

										# Сохраняем в память.
										await TelehooperAPI.save_message("VK", msg[0].message_id, event.message_id, False)

										assert msg[0].video_note, "Видеосообщение не было отправлено"

										return

									# Прикрепляем видео.
									attachment_media.append(InputMediaVideo(type="video", media=BufferedInputFile(video_bytes, filename=f"{attachment['title'].strip()} {quality[4:]}p.mp4")))

									break
								else:
									raise Exception("Не удалось получить ссылку на видео")
						elif attachment_type == "audio_message":
							attachment_media.append(InputMediaAudio(
								type="audio",
								media=attachment["link_ogg"]
							))
						elif attachment_type == "sticker":
							# В данный момент, поддержка анимированных стикеров отсутствует из-за возможного бага в библиотеке gzip.

							is_animated = "animation_url" in attachment and False # TODO: Настройка для отключения анимированных стикеров.
							attachment_cache_name = f"sticker{attachment['sticker_id']}{'anim' if is_animated else 'static'}"

							# Пытаемся получить информацию о данном стикере из кэша вложений.
							sticker_bytes = None
							cached_sticker = await TelehooperAPI.get_attachment("VK", attachment_cache_name)

							# Если стикер был найден в кэше, то скачиваем его.
							if not cached_sticker:
								logger.debug(f"Не был найден кэш для стикера с ID {attachment_cache_name}")

								# Достаём URL анимации стикера, либо статичное изображение-"превью" этого стикера.
								sticker_url = attachment.get("animation_url") if is_animated else attachment["images"][-1]["url"]

								# Загружаем стикер.
								async with aiohttp.ClientSession() as client:
									async with client.get(sticker_url) as response:
										assert response.status == 200, f"Не удалось загрузить стикер с ID {attachment_cache_name}"

										sticker_bytes = await response.read()

								# Делаем манипуляции над стикером, если он анимированный.
								if is_animated:
									# Этот кусок кода не используется.

									sticker_bytes = await utils.convert_to_tgs_sticker(sticker_bytes)

							# Отправляем стикер.
							msg = await subgroup.send_sticker(
								sticker=cached_sticker if cached_sticker else BufferedInputFile(
									file=cast(bytes, sticker_bytes),
									filename="sticker.tgs" if is_animated else f"VK sticker {attachment['sticker_id']}.png"
								),
								silent=is_outbox,
								reply_to=reply_to
							)

							# Если произошёл rate limit, то msg будет None.
							if not msg:
								return

							assert msg[0].sticker, "Стикер не был отправлен"

							# Сохраняем в память.
							await TelehooperAPI.save_message("VK", msg[0].message_id, event.message_id, False)

							# Кэшируем стикер, если настройка у пользователя это позволяет.
							if await self.user.get_setting("Security.MediaCache"):
								await TelehooperAPI.save_attachment("VK", attachment_cache_name, msg[0].sticker.file_id)

							return
						elif attachment_type == "doc":
							async with ChatActionSender(chat_id=subgroup.parent.chat.id, action="upload_document", bot=subgroup.parent.bot):
								async with aiohttp.ClientSession() as client:
									async with client.get(attachment["url"]) as response:
										assert response.status == 200, f"Не удалось загрузить документ с ID {attachment['id']}"

										file_bytes = b""
										while True:
											chunk = await response.content.read(1024)
											if not chunk:
												break

											file_bytes += chunk

											if len(file_bytes) > 50 * 1024 * 1024:
												logger.debug(f"Файл оказался слишком большой ({len(file_bytes)} байт).")

												raise Exception("Размер файла слишком большой")

								# Прикрепляем документ.
								attachment_media.append(InputMediaDocument(type="document", media=BufferedInputFile(file=file_bytes, filename=attachment["title"])))
						elif attachment_type == "audio":
							# Загружаем аудио.
							async with ChatActionSender(chat_id=subgroup.parent.chat.id, action="upload_audio", bot=subgroup.parent.bot):
								async with aiohttp.ClientSession() as client:
									async with client.get(attachment["url"]) as response:
										assert response.status == 200, f"Не удалось загрузить аудио с ID {attachment['id']}"

										video_bytes = b""

										while True:
											chunk = await response.content.read(1024)
											if not chunk:
												break

											video_bytes += chunk

											if len(video_bytes) > 50 * 1024 * 1024:
												logger.debug(f"Файл оказался слишком большой ({len(video_bytes)} байт).")

												raise Exception("Размер файла слишком большой")

								attachment_media.append(InputMediaAudio(
									type="audio",
									media=BufferedInputFile(
										file=video_bytes,
										filename=f"{attachment['artist']} - {attachment['title']}.mp3"
									),
									title=attachment["title"],
									performer=attachment["artist"]
								))
						elif attachment_type == "graffiti":
							attachment_media.append(InputMediaPhoto(type="photo", media=attachment["url"]))
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
						else:
							raise TypeError(f"Неизвестный тип вложения \"{attachment_type}\"")

			# Подготавливаем текст сообщения, который будет отправлен.
			full_message_text = ""
			msg_prefix = ""
			msg_suffix = ""

			if from_self or is_convo:
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

				if event.text:
					msg_prefix += ": "

			if attachment_items:
				msg_suffix += "\n\n————————\n"

				msg_suffix += "  |  ".join(attachment_items) + "."

			full_message_text = msg_prefix + utils.telegram_safe_str(event.text) + msg_suffix

			# Отправляем готовое сообщение, и сохраняем его ID в БД бота.
			async def _send_and_save() -> None:
				# Высылаем сообщение.
				msg = await subgroup.send_message_in(
					full_message_text,
					attachments=attachment_media,
					silent=is_outbox,
					reply_to=reply_to,
					keyboard=keyboard
				)

				# Если произошёл rate limit, то msg будет None.
				if not msg:
					return

				await TelehooperAPI.save_message("VK", msg, event.message_id, False)

			# Если у нас были вложения, то мы должны отправить сообщение с ними.
			if attachment_media:
				async with ChatActionSender.upload_document(chat_id=subgroup.parent.chat.id, bot=subgroup.parent.bot, initial_sleep=1):
					await _send_and_save()
			else:
				await _send_and_save()
		except Exception as e:
			logger.exception(f"Ошибка отправки сообщения Telegram-пользователю {utils.get_telegram_logging_info(self.user.telegramUser)}:", e)

			try:
				await subgroup.send_message_in(
					(
						"<b>⚠️ У бота произошла ошибка</b>.\n"
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
						text="Прочитать во ВКонтакте",
						url=message_url
					)]])
				)
			except:
				pass

	async def handle_typing(self, event: LongpollTypingEvent | LongpollTypingEventMultiple | LongpollVoiceMessageEvent) -> None:
		"""
		Обработчик события начала "печати" либо записи голосового сообщения во ВКонтакте.

		:param event: Событие типа `LongpollTypingEvent`, `LongpollTypingEventMultiple` или `LongpollVoiceMessageEvent`, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(self.user, ServiceDialogue(service_name=self.service_name, id=event.peer_id))

		# Проверяем, что у пользователя есть подгруппа, в которой нужно начать событие печати.
		if not subgroup:
			return

		logger.debug(f"[VK] Событие печати для подгруппы \"{subgroup.service_dialogue_name}\"")

		await subgroup.start_activity("record_audio" if type(event) is LongpollVoiceMessageEvent else "typing")

		# TODO: Если пользователей несколько, и в группе несколько Telehooper-ботов, то начать событие печати от имени разных ботов.

	async def handle_edit(self, event: LongpollMessageEditEvent) -> None:
		"""
		Обработчик события редактирования сообщения во ВКонтакте.

		:param event: Событие типа `LongpollMessageEditEvent`, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(self.user, ServiceDialogue(service_name=self.service_name, id=event.peer_id))

		# Проверяем, что у пользователя есть подгруппа, в которую можно отправить сообщение.
		if not subgroup:
			return

		logger.debug(f"[VK] Событие редактирования сообщения для подгруппы \"{subgroup.service_dialogue_name}\"")

		# Пытаемся получить ID сообщения в Telegram, которое нужно отредактировать.
		telegram_message = await subgroup.service.get_message_by_service_id(event.message_id)

		if not telegram_message:
			return

		# Редактируем сообщение.
		try:
			await subgroup.edit_message(f"{event.new_text}   <i>(ред.)</i>", telegram_message.telegram_message_ids[0])
		except:
			pass

		# TODO: При редактировании сообщения теряются префиксы и суфиксы от Telehooper.

	async def handle_message_flags_change(self, event: LongpollMessageFlagsEdit) -> None:
		"""
		Обработчик события изменения флагов у уже существующего сообщения во ВКонтакте.

		:param event: Событие типа `LongpollMessageFlagsEdit`, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		if not event.new_flags.outbox:
			return

		if not event.new_flags.delete_for_all:
			return

		subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(self.user, ServiceDialogue(service_name=self.service_name, id=event.peer_id))

		# Проверяем, что у пользователя есть подгруппа, в которую можно отправить сообщение.
		if not subgroup:
			return

		logger.debug(f"[VK] Событие удаления сообщения для подгруппы \"{subgroup.service_dialogue_name}\"")

		# Пытаемся получить ID сообщения в Telegram, которое нужно отредактировать.
		telegram_message = await subgroup.service.get_message_by_service_id(event.message_id)

		if not telegram_message:
			return

		# Удаляем сообщение.
		await subgroup.delete_message(telegram_message.telegram_message_ids)

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

			await self.vkAPI.messages_send(
				peer_id=db_user["Connections"]["VK"]["ID"],
				message="ℹ️ Telegram-бот «Telehooper» был отключён от Вашей страницы ВКонтакте."
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

	async def current_user_info(self) -> TelehooperServiceUserInfo:
		self_info = await self.vkAPI.get_self_info()

		return TelehooperServiceUserInfo(
			service_name=self.service_name,
			id=self_info["id"],
			name=f"{self_info['first_name']} {self_info['last_name']}",
			profile_url=self_info.get("photo_max_orig"),
		)

	async def get_user_info(self, user_id: int, force_update: bool = False) -> TelehooperServiceUserInfo:
		"""
		Возвращает информацию о пользователе ВКонтакте.

		:param user_id: ID пользователя ВКонтакте.
		:param force_update: Нужно ли обновить информацию о пользователе, если она уже есть в кэше.
		"""

		if not force_update and user_id in self._cachedUsersInfo:
			return self._cachedUsersInfo[user_id]

		user_info = (await self.vkAPI.users_get(user_ids=[user_id]))[0]

		user_info_class = TelehooperServiceUserInfo(
			service_name=self.service_name,
			id=user_info["id"],
			name=f"{user_info['first_name']} {user_info['last_name']}",
			profile_url=user_info.get("photo_max_orig")
		)
		self._cachedUsersInfo[user_id] = user_info_class

		return user_info_class

	async def get_dialogue(self, chat_id: int, force_update: bool = False) -> ServiceDialogue:
		dialogues = await self.get_list_of_dialogues(force_update=force_update)

		for dialogue in dialogues:
			if dialogue.id == chat_id:
				return dialogue

		raise TypeError(f"Диалог с ID {chat_id} не найден")

	async def set_online(self) -> None:
		await self.vkAPI.account_setOnline()

	async def start_activity(self, peer_id: int, type: Literal["typing", "audiomessage"] = "typing") -> None:
		await self.vkAPI.messages_setActivity(peer_id=peer_id, type=type)

	async def mark_as_read(self, peer_id: int) -> None:
		await self.vkAPI.messages_markAsRead(peer_id=peer_id)

	async def send_message(self, chat_id: int, text: str, reply_to_message: int | None = None, attachments: list[str] | str | None = None, latitude: float | None = None, longitude: float | None = None) -> int:
		return await self.vkAPI.messages_send(peer_id=chat_id, message=text, reply_to=reply_to_message, attachment=attachments, lat=latitude, long=longitude)

	async def handle_inner_message(self, msg: Message, subgroup: "TelehooperSubGroup", attachments: list[PhotoSize | Video | Audio | TelegramDocument | Voice | Sticker | VideoNote]) -> None:
		from api import TelehooperAPI


		message_text = msg.text or msg.caption or ""

		logger.debug(f"[TG] Обработка сообщения в Telegram: \"{message_text}\" в \"{subgroup}\" {'с вложениями' if attachments else ''}")

		reply_message_id = None
		if msg.reply_to_message:
			saved_message = await self.get_message_by_telegram_id(msg.reply_to_message.message_id)

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
				filenames: list[str] = []
				for index in range(0, len(attchs_of_same_type), multiple_uploads_amount):
					attchs_of_same_type_part = attchs_of_same_type[index:index + multiple_uploads_amount]

					upload_url: str | None = None
					ext: str | None = None
					if attch_type == "PhotoSize":
						upload_url = (await self.vkAPI.photos_getMessagesUploadServer(peer_id=subgroup.service_chat_id))["upload_url"]
						ext = "jpg"
					elif attch_type == "Voice":
						assert len(attachments) == 1, "Вложение типа Voice не может быть отправлено вместе с другими вложениями"

						upload_url = (await self.vkAPI.docs_getMessagesUploadServer(type="audio_message", peer_id=subgroup.service_chat_id))["upload_url"]
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
							upload_url = (await self.vkAPI.docs_getMessagesUploadServer(type="graffiti", peer_id=subgroup.service_chat_id))["upload_url"]
							ext = "png"

						# TODO: Изменение размера стикера что бы он не был слишком большим для ВК.
					elif attch_type == "Document":
						upload_url = (await self.vkAPI.docs_getMessagesUploadServer(type="doc", peer_id=subgroup.service_chat_id))["upload_url"]

						for file_same_type in attchs_of_same_type_part:
							filenames.append(cast(TelegramDocument, file_same_type).file_name or "unknown-filename.txt")
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

								form_data.add_field(name=field_name, value=file_bytes, filename=f"file{index}.{ext}" if ext else filenames.pop(0))

							# Отправляем загруженные вложения на сервера ВК.
							async with client.post(upload_url, data=form_data) as response:
								assert response.status == 200, f"Не удалось загрузить вложение типа {attch_type}"
								response = VKAPI._parse_response(await response.json(content_type=None), "_get.server_")

								attachments_results.append(response)

				# Закончили отправлять все вложения пачками по 5 элементов.
				# Говорим ВК, что мы хотим отправить вложения в сообщении.
				attachment_str_list: list[str] = []

				# Если мы уже извлекли вложение из кэша, то нам нужно просто их добавить в список.
				if attachment_value:
					attachment_str_list.append(attachment_value)
				else:
					for attachment in attachments_results:
						if attch_type == "PhotoSize":
							assert attachment["photo"], "Объект photo является пустым"
							resp = await self.vkAPI.photos_saveMessagesPhoto(photo=attachment["photo"], server=attachment["server"], hash=attachment["hash"])

							for saved_attch in resp:
								attachment_str_list.append(VKAPI.get_attachment_string("photo", saved_attch["owner_id"], saved_attch["id"], saved_attch.get("access_key")))
						elif attch_type == "Voice":
							saved_attch = (await self.vkAPI.docs_save(file=attachment["file"], title="Voice message"))["audio_message"]

							attachment_str_list.append(VKAPI.get_attachment_string("doc", saved_attch["owner_id"], saved_attch["id"], saved_attch.get("access_key")))
						elif attch_type in ["Video", "VideoNote"]:
							attachment_str_list.append(VKAPI.get_attachment_string("video", attachment["owner_id"], attachment["video_id"], attachment.get("access_key")))
						elif attch_type == "Sticker":
							saved_attch = (await self.vkAPI.docs_save(file=attachment["file"], title="Sticker"))["graffiti"]

							attachment_str = VKAPI.get_attachment_string("doc", saved_attch["owner_id"], saved_attch["id"], saved_attch.get("access_key"))
							attachment_str_list.append(attachment_str)

							# Стикеры нам нужно кэшировать, если пользователь это разрешил.
							if await self.user.get_setting("Security.MediaCache"):
								await TelehooperAPI.save_attachment("VK", f"sticker{attachments[0].file_unique_id}static", attachment_str)
						elif attch_type == "Document":
							saved_attch = (await self.vkAPI.docs_save(file=attachment["file"]))["doc"]

							attachment_str_list.append(VKAPI.get_attachment_string("doc", saved_attch["owner_id"], saved_attch["id"], saved_attch.get("access_key")))

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

		# Делаем статус "онлайн", если он не был обновлён в течении минуты.
		if utils.get_timestamp() - self._lastOnlineStatus > 60 and await self.user.get_setting("Services.VK.SetOnline"):
			self._lastOnlineStatus = utils.get_timestamp()

			asyncio.create_task(self.set_online())

		# Делаем статус "печати" и прочитываем сообщение.
		if await self.user.get_setting("Services.VK.WaitToType"):
			await asyncio.gather(self.mark_as_read(subgroup.service_chat_id), self.start_activity(subgroup.service_chat_id))

			await asyncio.sleep(0.6 if len(message_text) <= 15 else 1)

		# Отправляем сообщение.
		await TelehooperAPI.save_message("VK", msg.message_id, await self.send_message(
			chat_id=subgroup.service_chat_id,
			text=message_text,
			reply_to_message=reply_message_id,
			attachments=attachments_to_send,
			latitude=msg.location.latitude if msg.location else None,
			longitude=msg.location.longitude if msg.location else None
		), True)

	async def handle_message_delete(self, msg: Message, subgroup: "TelehooperSubGroup") -> None:
		from api import TelehooperAPI


		logger.debug(f"[TG] Обработка удаления сообщения в Telegram: \"{msg.text}\" в \"{subgroup}\"")

		saved_message = await self.get_message_by_telegram_id(msg.message_id)

		if not saved_message:
			await subgroup.send_message_in(
				"<b>⚠️ Ошибка удаления сообщения</b>.\n"
				"\n"
				"Сообщение не было найдено ботом, поэтому оно не было удалено.",
				silent=True
			)

			return

		try:
			await self.vkAPI.messages_delete(saved_message.service_message_ids)
		except AccessDeniedException:
			# TODO: Уточнить причину ошибки в зависимости от типа диалога.

			reason = "Прошло более 24-х часов с момента отправки сообщения."
			if not saved_message.sent_via_bot:
				reason = "Вы попытались удалить сообщение, отправленное Вашим собедеседником, либо же Вы не являетесь Администратором в беседе."

			await subgroup.send_message_in(
				"<b>⚠️ Ошибка удаления сообщения</b>.\n"
				"\n"
				f"{reason}",
				silent=True
			)

			return

		# Удаляем из кэша сообщений.
		await TelehooperAPI.delete_message(
			"VK",
			saved_message.service_message_ids
		)

	async def handle_message_edit(self, msg: Message, subgroup: "TelehooperSubGroup") -> None:
		logger.debug(f"[TG] Обработка редактирования сообщения в Telegram: \"{msg.text}\" в \"{subgroup}\"")

		saved_message = await self.get_message_by_telegram_id(msg.message_id)

		if not saved_message:
			await subgroup.send_message_in(
				"<b>⚠️ Ошибка редактирования сообщения</b>.\n"
				"\n"
				"Сообщение не было найдено ботом, поэтому оно не было отредактировано.",
				silent=True,
				reply_to=msg.message_id
			)

			return

		try:
			await self.vkAPI.messages_edit(
				message_id=saved_message.service_message_ids[0],
				peer_id=subgroup.service_chat_id,
				message=msg.text or "[пустой текст сообщения]"
			)
		except AccessDeniedException:
			await subgroup.send_message_in(
				"<b>⚠️ Ошибка редактирования сообщения</b>.\n"
				"\n"
				f"Сообщение слишком старое что бы его редактировать.",
				silent=True
			)

	async def handle_message_read(self, subgroup: "TelehooperSubGroup") -> None:
		logger.debug(f"[TG] Обработка прочтения сообщения в Telegram в \"{subgroup}\"")

		await self.mark_as_read(subgroup.service_chat_id)

	async def get_message_by_telegram_id(self, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		from api import TelehooperAPI

		return await TelehooperAPI.get_message_by_telegram_id("VK", message_id, bypass_cache=bypass_cache)

	async def get_message_by_service_id(self, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		from api import TelehooperAPI

		return await TelehooperAPI.get_message_by_service_id("VK", message_id, bypass_cache=bypass_cache)

	@staticmethod
	async def reconnect_on_restart(user: "TelehooperUser", db_user: Document, bot: Bot) -> "VKServiceAPI" | None:
		vkServiceAPI = None

		# Проверка, что токен установлен.
		# Токен может отсутствовать, если настройка Security.StoreTokens была выставлена в значение «выключено».
		if not db_user["Connections"]["VK"]["Token"]:
			# Удаляем сервис из БД.
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

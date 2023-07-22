# coding: utf-8

import asyncio
import html
import json
from typing import TYPE_CHECKING, Optional, cast

import aiohttp
from aiogram.types import (BufferedInputFile, Chat, FSInputFile, InputMediaAudio,
                           InputMediaDocument, InputMediaPhoto,
                           InputMediaVideo, Message)
from aiogram.utils.chat_action import ChatActionSender
from loguru import logger
from pydantic import SecretStr
from services.vk.exceptions import AccessDeniedException
from services.vk.utils import create_message_link

import utils
from config import config
from DB import get_user
from services.service_api_base import (BaseTelehooperServiceAPI,
                                       ServiceDialogue,
                                       ServiceDisconnectReason,
                                       TelehooperServiceUserInfo)
from services.vk.vk_api.api import VKAPI
from services.vk.vk_api.longpoll import (BaseVKLongpollEvent,
                                         LongpollNewMessageEvent,
                                         VKAPILongpoll)

if TYPE_CHECKING:
	from api import TelehooperMessage, TelehooperSubGroup, TelehooperUser


class VKServiceAPI(BaseTelehooperServiceAPI):
	"""
	Service-API для ВКонтакте.
	"""

	token: SecretStr
	"""Токен для доступа к API ВКонтакте."""
	vkAPI: VKAPI
	"""Объект для доступа к API ВКонтакте."""

	_cachedDialogues = []
	"""Кэшированный список диалогов."""
	_longPollTask: asyncio.Task | None = None
	"""Задача, выполняющая longpoll."""

	def __init__(self, token: SecretStr, vk_user_id: int, user: "TelehooperUser") -> None:
		super().__init__("VK", vk_user_id, user)

		self.token = token
		self.user = user

		self.vkAPI = VKAPI(self.token)

	async def start_listening(self) -> asyncio.Task:
		# TODO: Обработка ошибок этой функции. (asyncio.Task)

		async def _handle_updates() -> None:
			longpoll = VKAPILongpoll(self.vkAPI)

			async for event in longpoll.listen_for_updates():
				await self.handle_update(event)

		self._longPollTask = asyncio.create_task(_handle_updates())
		return self._longPollTask

	async def handle_update(self, event: BaseVKLongpollEvent) -> None:
		"""
		Метод, обрабатывающий события VK Longpoll.

		:param event: Событие, полученное с longpoll-сервера.
		"""

		from api import TelehooperAPI


		logger.debug(f"[VK] Новое событие {event.__class__.__name__}: {event.event_data}")

		if type(event) is LongpollNewMessageEvent:
			subgroup = TelehooperAPI.get_subgroup_by_service_dialogue(
				self.user,
				ServiceDialogue(
					service_name=self.service_name,
					id=event.peer_id
				)
			)

			# Проверяем, что у пользователя есть подгруппа в которую можно отправить текст сообщения.
			if not subgroup:
				return

			logger.debug(f"[VK] Сообщение с текстом \"{event.text}\", для подгруппы \"{subgroup.service_dialogue_name}\"")

			try:
				attachment_media: list[InputMediaAudio | InputMediaDocument | InputMediaPhoto | InputMediaVideo] = []
				sent_by_account_owner = event.flags.outbox
				ignore_self_debug = config.debug and await self.user.get_setting("Debug.SentViaBotInform")
				attachment_items: list[str] = []
				message_url = create_message_link(event.peer_id, event.message_id, use_mobile=False) # TODO: Настройка для использования мобильной версии сайта.

				# Проверяем, стоит ли боту обрабатывать исходящие сообщения.
				if sent_by_account_owner and not (await self.user.get_setting("Services.ViaServiceMessages") or ignore_self_debug):
					return

				# Получаем информацию о отправленном сообщении.
				msg_saved = await subgroup.service.get_message_by_service_id(event.message_id)

				# Проверяем, не было ли отправлено сообщение самим ботом.
				from_bot = msg_saved and msg_saved.sent_via_bot
				if from_bot and not ignore_self_debug:
					return

				# Получаем ID сообщения с ответом, а так же парсим вложения сообщения.
				reply_to = None

				# Парсим вложения.
				if event.attachments:
					attachments = event.attachments.copy()

					# Добываем полную информацию о сообщении.
					message_extended = (await self.vkAPI.messages_getById(event.message_id))["items"][0]

					# Обрабатываем ответы (reply).
					if "reply" in attachments:
						# Извлекаем ID сообщения, на которое был дан ответ.
						real_message_id = cast(int, message_extended["reply_message"]["id"])

						# Настоящий ID сообщения получен. Получаем информацию о сообщении с БД бота.
						reply_message_info = await subgroup.service.get_message_by_service_id(real_message_id)

						# Если информация о данном сообщении есть, то мы можем получить ID сообщения в Telegram.
						if reply_message_info:
							reply_to = reply_message_info.telegram_message_ids[0]

					# Обрабатываем гео-вложения.
					if "geo" in attachments:
						attachment = message_extended["geo"]

						# Высылаем сообщение.
						await TelehooperAPI.save_message(
							"VK",
							(await subgroup.send_geo(
								latitude=attachment["coordinates"]["latitude"],
								longitude=attachment["coordinates"]["longitude"],
								silent=sent_by_account_owner,
								reply_to=reply_to
							))[0].message_id,
							event.message_id,
							False
						)

						return

					# Проходимся по всем вложениям.
					if message_extended:
						for attachment in message_extended["attachments"]:
							attachment_type = attachment["type"]
							attachment = attachment[attachment["type"]]

							if attachment_type == "photo":
								attachment_media.append(InputMediaPhoto(
									type="photo",
									media=attachment["sizes"][-1]["url"]
								))
							elif attachment_type == "video":
								# Так как ВК не выдают прямую ссылку на видео, необходимо её извлечь из API.
								# Что важно, передать ссылку напрямую не получается, поскольку ВК проверяет
								# UserAgent и IP адрес, с которого был сделан запрос.

								async with ChatActionSender(chat_id=subgroup.parent.chat.id, action="upload_video", bot=subgroup.parent.bot):
									video = (await self.vkAPI.video_get(videos=f"{attachment['owner_id']}_{attachment['id']}_{attachment['access_key']}"))["items"][0]["files"]

									video_quality_list = ["mp4_720", "mp4_480", "mp4_360", "mp4_240", "mp4_144"]

									# Если пользователь разрешил использование видео в 1080p, то добавляем его в список.
									if await self.user.get_setting("Services.HDVideo"):
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

												audio_bytes = b""

												while True:
													chunk = await response.content.read(1024)
													if not chunk:
														break

													audio_bytes += chunk

													# Пытаемся найти самое большое видео, которое не превышает 50 МБ.
													if len(audio_bytes) > 50 * 1024 * 1024:
														if is_last:
															raise Exception("Размер видео слишком большой")

														logger.debug(f"Файл размером {quality} оказался слишком большой ({len(audio_bytes)} байт).")

														continue

										# Прикрепляем видео.
										attachment_media.append(InputMediaVideo(
											type="video",
											media=BufferedInputFile(
												audio_bytes,
												filename=f"{attachment['title'].strip()} {quality[4:]}p.mp4"
											)
										))

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
									silent=sent_by_account_owner,
									reply_to=reply_to
								)

								# Сохраняем в память.
								await TelehooperAPI.save_message(
									"VK",
									msg[0].message_id,
									event.message_id,
									False
								)

								assert msg[0].sticker, "Стикер не был отправлен"

								# Кэшируем стикер, если настройка у пользователя это позволяет.
								if await self.user.get_setting("Security.MediaCache"):
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
									attachment_media.append(InputMediaDocument(
										type="document",
										media=BufferedInputFile(
											file=file_bytes,
											filename=attachment["title"]
										)
									))
							elif attachment_type == "audio":
								# Загружаем аудио.
								async with ChatActionSender(chat_id=subgroup.parent.chat.id, action="upload_audio", bot=subgroup.parent.bot):
									async with aiohttp.ClientSession() as client:
										async with client.get(attachment["url"]) as response:
											assert response.status == 200, f"Не удалось загрузить аудио с ID {attachment['id']}"

											audio_bytes = b""

											while True:
												chunk = await response.content.read(1024)
												if not chunk:
													break

												audio_bytes += chunk

												if len(audio_bytes) > 50 * 1024 * 1024:
													logger.debug(f"Файл оказался слишком большой ({len(audio_bytes)} байт).")

													raise Exception("Размер файла слишком большой")

									attachment_media.append(InputMediaAudio(
										type="audio",
										media=BufferedInputFile(
											file=audio_bytes,
											filename=f"{attachment['artist']} - {attachment['title']}.mp3"
										),
										title=attachment["title"],
										performer=attachment["artist"]
									))
							elif attachment_type == "wall":
								# TODO: Имя группы/юзера откуда был пост.
								#   В данный момент почти нереализуемо из-за того, что ВК не передаёт такую информацию, и нужно делать отдельный запрос.
								# TODO: Настройка, что бы показывать содержимое поста, а не ссылку на него.

								attachment_items.append(f"<a href=\"vk.com/wall{attachment['owner_id']}_{attachment['id']}\">🔄 Запись от {'пользователя' if attachment['owner_id'] > 0 else 'группы'}</a>")
							elif attachment_type == "link":
								# TODO: Проверить, какая первая ссылка есть в сообщении, и если она не совпадает с этой - сделать невидимую ссылку в самом начале.

								pass
							elif attachment_type == "poll":
								attachment_items.append(f"<a href=\"{message_url}\">📊 Опрос: «{attachment['question']}»</a>")
							elif attachment_type == "gift":
								attachment_media.append(InputMediaPhoto(
									type="photo",
									media=attachment["thumb_256"]
								))

								attachment_items.append(f"<a href=\"{message_url}\">🎁 Подарок</a>")
							elif attachment_type == "market":
								attachment_items.append(f"<a href=\"{message_url}\">🛒 Товар: «{attachment['title']}»</a>")
							elif attachment_type == "market_album":
								pass
							elif attachment_type == "wall_reply":
								attachment_items.append(f"<a href=\"{message_url}\">📝 Комментарий к записи</a>")
							else:
								raise TypeError(f"Неизвестный тип вложения \"{attachment_type}\"")

				# Подготавливаем текст сообщения.
				new_message_text = ""

				if sent_by_account_owner:
					new_message_text = f"[<b>Вы</b>"

					if ignore_self_debug and from_bot:
						new_message_text += " <i>debug-пересылка</i>"

					new_message_text += "]"

					if event.text:
						new_message_text += ": "

				new_message_text += utils.telegram_safe_str(event.text)

				if attachment_items:
					new_message_text += "\n\n————————\n"

					new_message_text += "  |  ".join(attachment_items) + "."

				# Отправляем готовое сообщение, и сохраняем его ID в БД бота.
				async def _send_and_save() -> None:
					await TelehooperAPI.save_message(
						"VK",
						await subgroup.send_message_in(
							new_message_text,
							attachments=attachment_media,
							silent=sent_by_account_owner,
							reply_to=reply_to
						),
						event.message_id,
						False
					)

				# Если у нас были вложения, то мы должны отправить сообщение с ними.
				if attachment_media:
					async with ChatActionSender.upload_document(chat_id=subgroup.parent.chat.id, bot=subgroup.parent.bot, initial_sleep=1):
						await _send_and_save()
				else:
					await _send_and_save()
			except Exception as e:
				# TODO: Отправлять сообщение об ошибке пользователю, делая при этом логирование самого текста ошибки.

				logger.error(f"Ошибка отправки сообщения Telegram-пользователю {utils.get_telegram_logging_info(self.user.telegramUser)}: {e}")

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
				extendedInfo.update({
					-group["id"]: group
				})

			for user in response.get("profiles", []):
				extendedInfo.update({
					user["id"]: user
				})

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
						is_muted="push_settings" in convo and convo["push_settings"]["disabled_forever"]
					)
				)

				retrieved_dialogues += 1

			if retrieved_dialogues >= total_dialogues or retrieved_dialogues >= max_amount:
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
		del self.token
		del self.vkAPI
		del self._cachedDialogues
		del self._longPollTask

	async def current_user_info(self) -> TelehooperServiceUserInfo:
		self_info = await self.vkAPI.get_self_info()

		return TelehooperServiceUserInfo(
			service_name=self.service_name,
			id=self_info["id"],
			name=f"{self_info['first_name']} {self_info['last_name']}",
			profile_url=self_info.get("photo_max_orig"),
		)

	async def get_dialogue(self, chat_id: int, force_update: bool = False) -> ServiceDialogue:
		dialogues = await self.get_list_of_dialogues(force_update=force_update)

		for dialogue in dialogues:
			if dialogue.id == chat_id:
				return dialogue

		raise TypeError(f"Диалог с ID {chat_id} не найден")

	async def send_message(self, chat_id: int, text: str, reply_to_message: int | None = None) -> int:
		return await self.vkAPI.messages_send(peer_id=chat_id, message=text, reply_to=reply_to_message)

	async def handle_inner_message(self, msg: Message, subgroup: "TelehooperSubGroup") -> None:
		from api import TelehooperAPI


		logger.debug(f"[TG] Обработка сообщения в Telegram: \"{msg.text}\" в \"{subgroup}\"")

		reply_message_id = None
		if msg.reply_to_message:
			saved_message = await self.get_message_by_telegram_id(msg.reply_to_message.message_id)

			reply_message_id = saved_message.service_message_ids[0] if saved_message else None

		service_message_id = await self.send_message(
			chat_id=subgroup.service_chat_id,
			text=msg.text or "[пустой текст сообщения]",
			reply_to_message=reply_message_id
		)
		await TelehooperAPI.save_message("VK", msg.message_id, service_message_id, True)

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

		await self.vkAPI.messages_markAsRead(subgroup.service_chat_id)

	async def get_message_by_telegram_id(self, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		from api import TelehooperAPI

		return await TelehooperAPI.get_message_by_telegram_id("VK", message_id, bypass_cache=bypass_cache)

	async def get_message_by_service_id(self, message_id: int, bypass_cache: bool = False) -> Optional["TelehooperMessage"]:
		from api import TelehooperAPI

		return await TelehooperAPI.get_message_by_service_id("VK", message_id, bypass_cache=bypass_cache)

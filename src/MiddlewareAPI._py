# coding: utf-8

# В этом файле находится middle-псевдо-API, благодаря которому различные 'коннекторы' могут соединяться с основым Telegram ботом.


from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List, Literal, Tuple

import aiogram

import Utils
from Consts import AccountDisconnectType
from DB import getDefaultCollection

if TYPE_CHECKING:
	from ServiceMAPIs.VK import VKAccount, VKMiddlewareAPI
	from TelegramBot import DialogueGroup, Telehooper

logger = logging.getLogger(__name__)

# TODO: Перенести этот класс в TelegramBot.py
class TelehooperUser:
	"""
	Класс, отображающий пользователя бота Telehooper: тут будут все подключённые сервисы.
	"""

	TGUser: aiogram.types.User
	bot: Telehooper

	vkAccount: VKAccount
	vkMAPI: "VKMiddlewareAPI"
	isVKConnected: bool

	def __init__(self, bot: Telehooper, user: aiogram.types.User) -> None:
		self.TGUser = user
		self.bot = bot
		self.vkAccount = None # type: ignore
		self.vkMAPI = None # type: ignore
		self.isVKConnected = False


	async def restoreFromDB(self) -> None:
		"""
		Восстанавливает данные, а так же подключенные сервисы из ДБ.
		"""

		DB = getDefaultCollection()

		res = DB.find_one({"_id": self.TGUser.id})
		if res and res["Services"]["VK"]["Auth"]:
			# Аккаунт ВК подключён.

			# Подключаем ВК:
			await self.connectVKAccount(res["Services"]["VK"]["Token"], res["Services"]["VK"]["IsAuthViaPassword"])

	async def connectVKAccount(self, token: str, auth_via_password: bool, connect_longpoll: bool = True) -> VKAccount:
		"""
		Подключает новый аккаунт ВК.
		"""

		# Я ненавижу Python.
		from ServiceMAPIs.VK import VKAccount, VKMiddlewareAPI

		# Авторизуемся в ВК:
		self.vkAccount = VKAccount(token, self, auth_via_password)
		await self.vkAccount.initUserInfo()

		await asyncio.sleep(0) # Спим 0 секунд, что бы последующий код не запускался до завершения кода выше.

		self.vkMAPI = VKMiddlewareAPI(self, self.bot)

		self.isVKConnected = True

		if connect_longpoll:
			self.vkMAPI.runPolling()

		return self.vkAccount

	async def getDialogueGroupByTelegramGroup(self, telegram_group: aiogram.types.Chat | int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		return await self.bot.getDialogueGroupByTelegramGroup(telegram_group)

	async def getDialogueGroupByServiceDialogueID(self, service_dialogue_id: int) -> DialogueGroup | None:
		"""
		Возвращает диалог-группу по ID группы Telegram, либо же `None`, если ничего не было найдено.
		"""

		return await self.bot.getDialogueGroupByServiceDialogueID(service_dialogue_id)

	def __str__(self) -> str:
		return f"<TelehooperUser id:{self.TGUser.id}>"

class MiddlewareAPI:
	"""
	Класс, являющийся объединением всех сервисов, в частности, их API, например, отправки сообщений, ...
	"""

	user: TelehooperUser
	bot: Telehooper

	def __init__(self, user: TelehooperUser, bot: Telehooper) -> None:
		self.user = user
		self.bot = bot


	async def onNewRecievedMessage(self, messageText: str) -> None:
		"""
		Событие, когда в сервисе получено новое сообщение.
		"""

		pass

	async def onMessageEdit(self) -> None:
		"""
		Событие, когда в сервисе сообщение отредактировалось.
		"""

		pass

	async def onChatTypingState(self, chat_id: int) -> None:
		"""
		Событие, когда в сервисе в каком-либо чате происходит событие по типу печатанья.
		"""

		pass

	async def sendMessageIn(self, text: str, chat_id: int | str, attachments: None | List[Utils.File] = None, reply_to: int | str | None = None, allow_sending_temp_messages: bool = True, return_only_first_element: bool = False) -> aiogram.types.Message | List[aiogram.types.Message]:
		"""
		Отправляет сообщение в Telegram.
		"""

		def _return(variable):
			"""
			Возвращает первый элемент, если это массив, и `return_only_first_element` - True.
			"""

			if return_only_first_element and isinstance(variable, list):
				return variable[0]
			else:
				return variable

		# Фиксы:
		if attachments is None:
			attachments = []
		reply_to = reply_to if reply_to is None else int(reply_to)

		# Проверяем, есть ли у нас вложения, которые стоит отправить:
		if len(attachments) > 0:
			tempMediaGroup = aiogram.types.MediaGroup()
			loadingCaption = "<i>Весь контент появится здесь после загрузки, подожди...</i>\n\n" + text

			# Если мы можем отправить временные сообщения, то отправляем их:
			if allow_sending_temp_messages and len(attachments) > 1:

				fileID: str | None = None
				tempMessages: List[aiogram.types.Message] = []
				DB = getDefaultCollection()

				# Пытаемся достать fileID временной фотки из ДБ:
				res = DB.find_one({"_id": "_global"})
				if res:
					fileID = res["TempDownloadImageFileID"]

				# Добавляем временные вложения:
				for index in range(len(attachments)):

					# Проверяем, есть ли у нас в ДБ идентификатор для временного файла. Если да,
					# то добавляем caption только на первом элементе, в ином случае Telegram
					# не покажет нам текст сообщения.
					#
					# Как бы я не хвалил Telegram, технические решения здесь отвратительны.
					if fileID:
						tempMediaGroup.attach(aiogram.types.InputMediaPhoto(fileID, loadingCaption if index == 0 else None))
					else:
						tempMediaGroup.attach(aiogram.types.InputMediaPhoto(aiogram.types.InputFile("downloadImage.png"), loadingCaption if index == 0 else None))

				# Отправляем файлы с временными сообщениями, которые мы заменим реальными вложениями.
				tempMessages = await self.user.TGUser.bot.send_media_group(chat_id, tempMediaGroup, reply_to_message_id=reply_to)

				# Если же у нас таковой нет, то мы сохраняем ID временной фотки в ДБ:
				if not fileID:
					DB.update_one({"_id": "_global"}, {
						"$set": {
							"TempDownloadImageFileID": tempMessages[0].photo[-1].file_id
						}
					})

				# Теперь нам стоит отредачить сообщение с новыми вложениями.
				# Я специально редактирую всё с конца, что бы не трогать лишний раз caption
				# самого первого сообщения.
				for index, attachment in reversed(list(enumerate(attachments))):

					await self.startChatActionStateIn(chat_id, "upload_photo")

					# Загружаем файл, если он не был загружен:
					if not attachment.ready:
						await attachment.parse()

					# Заменяем старый временный файл на новый:
					await tempMessages[index].edit_media(
						aiogram.types.InputMedia(
							media=attachment.aiofile, caption=text if index == 0 else None
						)
					)

					# Каждый запрос спим, что бы не превысить лимит:
					await asyncio.sleep(1)

				return _return(tempMessages)
			else:
				# Если мы не можем отправить временные сообщения, то добавляем их по одному в MediaGroup:

				for index, attachment in enumerate(attachments):
					if not attachment.ready:
						await attachment.parse()

					MEDIA_TYPES = ["photo", "video", "document", "animation"]

					if attachment.type in MEDIA_TYPES:
						tempMediaGroup.attach(aiogram.types.InputMedia(media=attachment.aiofile, caption=text if index == 0 else None))
					elif attachment.type == "voice":
						return _return(await self.user.TGUser.bot.send_voice(chat_id, attachment.aiofile, reply_to_message_id=reply_to, ))



				# И после добавления в MediaGroup, отправляем сообщение:
				await self.startChatActionStateIn(chat_id, "upload_photo")

				return _return(await self.user.TGUser.bot.send_media_group(chat_id, tempMediaGroup, reply_to_message_id=reply_to))

		# У нас нет никакой группы вложений, поэтому мы просто отправим сообщение:
		return _return(await self.user.TGUser.bot.send_message(chat_id, text, reply_to_message_id=reply_to))

	async def sendMessageOut(self, message: str) -> None:
		"""
		Отправляет сообщение в сервисе.
		"""

		pass

	async def editMessageIn(self, message: str, chat_id: int, message_id: int) -> None:
		"""
		Редактирует сообщение в Telegram.
		"""

		await self.user.TGUser.bot.edit_message_text(message, chat_id, message_id)

	async def editMessageOut(self, message: str, message_id: int) -> None:
		"""
		Редактирует сообщение в сервисе.
		"""

		pass

	async def sendServiceMessageIn(self, message: str) -> aiogram.types.Message:
		"""
		Отправляет сообщению пользователю в Telegram. При использовании функции, сообщение появится у пользователя в диалоге с ботом.
		"""

		return await self.user.TGUser.bot.send_message(self.user.TGUser.id, message)

	async def sendServiceMessageOut(self, message: str) -> None:
		"""
		Отправляет сообщение внутри сервиса. Это не обычная отправка сообщения конкретному пользователю, данная функция отправляет сообщение пользователю к самому себе; например, во ВКонтакте, сообщение будет отправлено в диалог "избранное".
		"""

		pass

	async def startChatActionStateIn(self, chat_id: int | str, action: Literal["typing", "upload_photo", "record_video", "upload_video", "record_voice", "upload_voice", "upload_document", "find_location", "record_video_note", "upload_video_note"] = "typing") -> None:
		"""
		Начинает какое либо действие в чате, к примеру, действие "печати" в Telegram.
		"""

		await self.user.TGUser.bot.send_chat_action(chat_id, action)

	async def startChatActionStateOut(self, chat_id: int | str, action: str):
		"""
		Начинает какое либо действие в чате, к примеру, действие "печати" в сервисе.
		"""

		pass

	async def disconnectService(self, disconnect_type: int = AccountDisconnectType.INITIATED_BY_USER, send_service_messages: bool = True) -> None:
		"""
		Отключает сервис от бота.
		"""

		if disconnect_type != AccountDisconnectType.SILENT:
			# Это не было "тихое" отключение аккаунта, поэтому
			# отправляем сообщения пользователю Telegram.

			is_external = (disconnect_type == AccountDisconnectType.EXTERNAL)

			await self.user.TGUser.bot.send_message(
				self.user.TGUser.id,
				(
					"<b>Аккаунт был отключён от Telehooper</b> ⚠️\n\nАккаунт <b>«ВКонтакте»</b> был отключён от бота. Действие было произведено <b>внешне</b>, например, путём отзыва всех сессий в <b>настройках безопасности аккаунта</b>."
					if (is_external) else
					"<b>Аккаунт был отключён от Telehooper</b> ℹ️\n\nАккаунт <b>«ВКонтакте»</b> был успешно отключён от бота. Очень жаль, что так вышло."
				)
			)

		# Получаем ДБ:
		DB = getDefaultCollection()

		# И удаляем запись оттуда:
		DB.update_one(
			{
				"_id": self.user.TGUser.id
			},
			{"$set": {
				"Services.VK.Auth": False,
				"Services.VK.Token": None,
				"Services.VK.IsAuthViaPassword": None,
				"Services.VK.AuthDate": None,
				"Services.VK.ID": None,
				"Services.VK.DownloadImage": None,
				"Services.VK.ServiceToTelegramMIDs": []
			}},
			upsert=True
		)

	def saveMessageID(self, telegram_message_id: int | str, service_message_id: int | str, telegram_dialogue_id: int | str, service_dialogue_id: int | str, sent_via_telegram: bool) -> None:
		"""Сохраняет ID сообщения в базу."""

		# Сохраняем ID сообщения в ДБ:
		DB = getDefaultCollection()
		DB.update_one({"_id": self.user.TGUser.id}, {
			"$push": {
				"Services.VK.ServiceToTelegramMIDs": {
					"TelegramMID": str(telegram_message_id),
					"ServiceMID": str(service_message_id),
					"TelegramDialogueID": str(telegram_dialogue_id),
					"ServiceDialogueID": str(service_dialogue_id),
					"ViaTelegram": sent_via_telegram
				}
			}
		})

		# Сохраняем ID последнего сообщения.
		self.bot.saveLatestMessageID(telegram_dialogue_id, telegram_message_id, service_message_id)

	def getMessageIDByTelegramMID(self, telegram_message_id: int | str) -> None | Tuple[int, int, int, int]:
		"""Достаёт ID сообщения сервиса по ID сообщения Telegram. В случае успеха выводит класс с значениями: `telegram_message_id`, `service_message_id`, `telegram_chat_id`, `service_chat_id`."""

		pass

	def getMessageDataByServiceMID(self, service_message_id: int | str) -> None | Tuple[int, int, int, int]:
		"""Достаёт ID сообщения Telegram по ID сообщения сервиса. В случае успеха выводит класс с значениями: `telegram_message_id`, `service_message_id`, `telegram_chat_id`, `service_chat_id`."""

		pass

	def _getMessageDataByKeyname(self, key: int | str, value: int | str) -> None | Tuple[int, int, int, int]:
		"""
		Ищет информацию о сообщении (ID, Chat ID, ...) по ключу и значению.
		"""

		pass




	def __str__(self) -> str:
		return "<Base MiddlewareAPI class>"

class MappedMessage:
	"""
	Класс, показывающий ID сообщений сервиса и его ID в Telegram.
	"""

	sentViaTelegram: bool
	sentViaService: bool

	telegramMID: int
	serviceMID: int
	telegramDialogueID: int
	serviceDialogueID: int

	def __init__(self, telegram_message_id: int, service_message_id: int, telegram_dialogue_id: int, service_dialogue_id: int, sent_via_telegram: bool) -> None:
		self.telegramMID = telegram_message_id
		self.serviceMID = service_message_id
		self.telegramDialogueID = telegram_dialogue_id
		self.serviceDialogueID = service_dialogue_id
		self.sentViaTelegram = sent_via_telegram
		self.sentViaService = not self.sentViaTelegram

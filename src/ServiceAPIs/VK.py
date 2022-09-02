# coding: utf-8

from __future__ import annotations

import asyncio
import datetime
import io
import os
from asyncio import Task
from typing import TYPE_CHECKING, Any, List, Literal, cast

import aiogram
import aiohttp
import Utils
import vkbottle
from Consts import AccountDisconnectType
from DB import getDefaultCollection
from loguru import logger
from PIL import Image
from vkbottle.user import Message
from vkbottle_types.objects import MessagesGraffiti
from vkbottle_types.responses.groups import GroupsGroupFull
from vkbottle_types.responses.messages import MessagesConversationWithMessage
from vkbottle_types.responses.users import UsersUserFull
from .Base import BaseTelehooperAPI, MappedMessage

if TYPE_CHECKING:
	from TelegramBot import Telehooper, TelehooperUser

class VKTelehooperAPI(BaseTelehooperAPI):
	"""
	API для работы над ВКонтакте.
	"""

	def __init__(self, telehooper_bot: "Telehooper") -> None:
		super().__init__(telehooper_bot)

		self.available = True
		self.serviceCodename = "vk"

	async def connect(self, user: "TelehooperUser", token: str, connect_via_password: bool = False, send_connection_message: bool = False):
		await super().connect(user)

		# Пытаемся подключиться к странице ВК:
		await self.reconnect(user, token, False)

		# Отправляем сообщения о успешном присоединении:
		if send_connection_message:
			await self._sendSuccessfulConnectionMessage(user, connect_via_password)

		# Сохраняем инфу в ДБ:
		await self._saveConnectedUserToDB(user, token, connect_via_password)

		# Вызываем метод API бота:
		await self.onSuccessfulConnection(user)

	async def reconnect(self, user: "TelehooperUser", token: str, call_onSuccessfulConnection_method: bool = True):
		await super().reconnect(user)

		# Пытаемся подключиться к странице ВК:
		vkAccountAPI = vkbottle.API(token)

		accountInfo = await vkAccountAPI.account.get_profile_info()
		fullUserInfo = await vkAccountAPI.users.get(
			user_ids=[accountInfo.id], 
			fields=["activities", "about", "blacklisted", "blacklisted_by_me", "books", "bdate", "can_be_invited_group", "can_post", "can_see_all_posts", "can_see_audio", "can_send_friend_request", "can_write_private_message", "career", "common_count", "connections", "contacts", "city", "country", "crop_photo", "domain", "education", "exports", "followers_count", "friend_status", "has_photo", "has_mobile", "home_town", "photo_100", "photo_200", "photo_200_orig", "photo_400_orig", "photo_50", "sex", "site", "schools", "screen_name", "status", "verified", "games", "interests", "is_favorite", "is_friend", "is_hidden_from_feed", "last_seen", "maiden_name", "military", "movies", "music", "nickname", "occupation", "online", "personal", "photo_id", "photo_max", "photo_max_orig", "quotes", "relation", "relatives", "timezone", "tv", "universities"]
		)
		await asyncio.sleep(1)

		# Если мы дошли до этого момента, значит, что страница подключена, и токен верный.
		
		user.APIstorage.vk.accountInfo = accountInfo
		user.APIstorage.vk.fullUserInfo = fullUserInfo[0]
		user.vkAPI = vkAccountAPI
		user.vkUser = vkbottle.User(token)

		# Запускаем longpoll:
		await self.runPolling(user)

		# Сохраняем то, что у пользователя подключён ВК:
		user.isVKConnected = True

		# Вызываем метод API бота:
		if call_onSuccessfulConnection_method:
			await self.onSuccessfulConnection(user)

	async def disconnect(self, user: "TelehooperUser", reason: int = AccountDisconnectType.INITIATED_BY_USER):
		await super().disconnect(user)

		self.stopPolling(user)

		user.isVKConnected = False

		if reason not in [AccountDisconnectType.ERRORED, AccountDisconnectType.SILENT]:
			# Мы должны отправить сообщения в самом сервисе о отключении:
			self.telehooper_bot.vkAPI = cast(VKTelehooperAPI, self.telehooper_bot.vkAPI)

			await self.telehooper_bot.vkAPI.sendMessage(
				user,
				message="ℹ️ Ваш аккаунт ВКонтакте был успешно отключён от бота «Telehooper».\n\nНадеюсь, что ты в скором времени вернёшься 🥺"
			)

			await self.telehooper_bot.sendMessage(
				user,
				(
					"<b>Аккаунт был отключён от Telehooper</b> ⚠️\n\nАккаунт <b>«ВКонтакте»</b> был отключён от бота. Действие было произведено <b>внешне</b>, например, путём отзыва всех сессий в <b>настройках безопасности аккаунта</b>."
					if (reason == AccountDisconnectType.EXTERNAL) else
					"<b>Аккаунт был отключён от Telehooper</b> ℹ️\n\nАккаунт <b>«ВКонтакте»</b> был успешно отключён от бота. Очень жаль, что так вышло."
				)
			)

		# Получаем ДБ:
		DB = getDefaultCollection()

		# И удаляем запись оттуда:
		DB.update_one(
			{
				"_id": user.TGUser.id
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

		await self.onDisconnect(user)

	async def runPolling(self, user: "TelehooperUser") -> Task:
		"""
		Запускает Polling для получения сообщений.
		"""

		if user.APIstorage.vk.pollingTask:
			# Polling уже запущен, не делаем ничего.

			logger.warning(f"Была выполнена попытка повторного запуска polling'а у пользователя с TID {user.TGUser.id}")

			return user.APIstorage.vk.pollingTask

		@user.vkUser.on.message()
		async def _onMessage(msg: Message):
			"""
			Вызывается при получении нового сообщения.
			"""

			await self.onNewMessage(user, msg)

		@user.vkUser.error_handler.register_error_handler(vkbottle.VKAPIError[5])
		async def _errorHandler(error: vkbottle.VKAPIError):
			"""
			Вызывается при отзыве разрешений у VK me / Kate Mobile.
			"""

			# Отправляем различные сообщения о отключённом боте:
			await self.disconnect(user, AccountDisconnectType.EXTERNAL)
			
		@user.vkUser.on.raw_event(vkbottle.UserEventType.MESSAGE_EDIT) # type: ignore
		async def _onMessageEdit(msg):
			await self.onMessageEdit(user, msg)

		@user.vkUser.on.raw_event(vkbottle.UserEventType.DIALOG_TYPING_STATE) # type: ignore
		async def _onDialogTypingState(msg):
			# Dialog - чат с человеком.

			await self.onDialogueActivity(user, msg.object[1], "typing")

		@user.vkUser.on.raw_event(vkbottle.UserEventType.CHAT_TYPING_STATE) # type: ignore
		async def _onChatTypingState(msg):
			# Chat - чат с беседой.

			await self.onDialogueActivity(user, msg.object[1], "typing")

		@user.vkUser.on.raw_event(vkbottle.UserEventType.CHAT_VOICE_MESSAGE_STATES) # type: ignore
		async def _onChatVoiceMessageState(msg):
			await self.onDialogueActivity(user, msg.object[1], "voice")

		@user.vkUser.on.raw_event(vkbottle.UserEventType.FILE_UPLOAD_STATE) # type: ignore
		async def _onChatFileUploadState(msg):
			await self.onDialogueActivity(user, msg.object[1], "file")

		@user.vkUser.on.raw_event(vkbottle.UserEventType.VIDEO_UPLOAD_STATE) # type: ignore
		async def _onChatVideoUploadState(msg):
			await self.onDialogueActivity(user, msg.object[1], "video")

		@user.vkUser.on.raw_event(vkbottle.UserEventType.PHOTO_UPLOAD_STATE) # type: ignore
		async def _onChatPhotoUploadState(msg):
			await self.onDialogueActivity(user, msg.object[1], "photo")

		@user.vkUser.on.raw_event(vkbottle.UserEventType.MESSAGES_DELETE) # type: ignore
		async def _onMessageDelete(msg):
			# Данный метод, похоже, не вызывается.

			logger.warning(f"Метод _onMessageDelete был вызван, хотя не должен был: {msg}")

		@user.vkUser.on.raw_event(vkbottle.UserEventType.INSTALL_MESSAGE_FLAGS) # type: ignore
		async def _onMessageFlagsChange(msg):
			# Вызывается в случае изменения информации о сообщении.

			IS_DELETED = Utils.getVKMessageFlags(msg.object[2])[7]

			# Если же сообщение было удалено, то выполняем на это функцию:
			if IS_DELETED:
				await self.onMessageDelete(user, msg)

		# Создаём Polling-задачу:
		user.APIstorage.vk.pollingTask = asyncio.create_task(user.vkUser.run_polling(), name=f"VK Polling, id{user.APIstorage.vk.accountInfo.id}") # type: ignore

		return user.APIstorage.vk.pollingTask

	def stopPolling(self, user: "TelehooperUser") -> None:
		"""
		Останавливает Polling.
		"""

		if not user.APIstorage.vk.pollingTask:
			return

		user.APIstorage.vk.pollingTask.cancel()

	def saveMessageID(self, user: "TelehooperUser", telegram_message_id: int | str, vk_message_id: int | str, telegram_dialogue_id: int | str, vk_dialogue_id: int | str, is_sent_via_telegram: bool) -> None:
		super().saveMessageID(user, "VK", telegram_message_id, vk_message_id, telegram_dialogue_id, vk_dialogue_id, is_sent_via_telegram)

		# Сохраняем ID последнего сообщения.
		self.telehooper_bot.vkAPI = cast("VKTelehooperAPI", self.telehooper_bot.vkAPI)
		self.telehooper_bot.vkAPI.saveLatestMessageID(user, "VK", telegram_dialogue_id, telegram_message_id, vk_message_id)

	async def retrieveDialoguesList(self, user: "TelehooperUser") -> List[VKDialogue]:
		"""
		Получает список всех диалогов пользователя, а так же кэширует их.
		"""

		convos = await user.vkAPI.messages.get_conversations(offset=0, count=200, extended=True)
		convos_extended_info = {}

		for vkGroup in convos.groups or {}:
			convos_extended_info.update({
				-vkGroup.id: vkGroup
			})

		for vkUser in convos.profiles or {}:
			convos_extended_info.update({
				vkUser.id: vkUser
			})

		user.APIstorage.vk.dialogues = []
		for convo in convos.items or {}:
			extended_info = convos_extended_info.get(convo.conversation.peer.id)

			user.APIstorage.vk.dialogues.append(VKDialogue(convo, extended_info, user.APIstorage.vk.accountInfo.id)) # type: ignore


		return user.APIstorage.vk.dialogues

	def getDialogueByID(self, user: "TelehooperUser", dialogue_id: int) -> VKDialogue | None:
		"""
		Возвращает диалог ВК по его ID. Используется во время преобразования группы в диалог-группу.
		"""

		if not user.APIstorage.vk.dialogues:
			return None

		for dialogue in user.APIstorage.vk.dialogues:
			if dialogue.ID == dialogue_id:
				return dialogue

		return None

	async def _commandHandler(self, user: "TelehooperUser", msg: Message) -> int | aiogram.types.Message:
		"""
		Обработчик команд отправленных внутри чата "Избранное" в ВК.
		"""

		async def _commandRecieved(msg: Message):
			await user.vkAPI.messages.edit(user.APIstorage.vk.accountInfo.id, "✅ " + msg.text, message_id=msg.id) # type: ignore

		if msg.text.startswith("logoff"):
			# Выходим из аккаунта:
			await _commandRecieved(msg)

			await self.disconnect(user, AccountDisconnectType.EXTERNAL)

			# await self.sendServiceMessageOut("ℹ️ Ваш аккаунт ВКонтакте был успешно отключён от бота «Telehooper».", msg.id)
			return 0
		elif msg.text.startswith("test"):
			await _commandRecieved(msg)

			# await self.sendServiceMessageOut("✅ Telegram-бот «Telehooper» работает!", msg.id)
			return 0
		elif msg.text.startswith("ping"):
			await _commandRecieved(msg)

			# return await self.sendServiceMessageIn("[<b>ВКонтакте</b>] » Проверка связи! 👋")
		else:
			# Неизвестная команда.

			return 0

		return 0

	async def onNewMessage(self, user: "TelehooperUser", msg: Message):
		await super().onNewMessage(user)

		if user.APIstorage.vk.fullUserInfo is None:
			# Полная информация о пользователе ещё не была получена.

			logger.warning("fullUserInfo is None.")

			return

		if msg.peer_id == user.APIstorage.vk.fullUserInfo.id:
			# Мы получили сообщение в "Избранном", обрабатываем сообщение как команду,
			# но боту в ТГ ничего не передаём.
			tg_message = await self._commandHandler(user, msg)

			if tg_message and isinstance(tg_message, aiogram.types.Message):
				# Сообщение в Телеграм.

				# self.saveMessageID(tg_message.message_id, msg.message_id, tg_message.chat.id, msg.chat_id, False)
				pass


			return

		if abs(msg.peer_id) == int(os.environ.get("VKBOT_NOTIFIER_ID", 0)):
			# Мы получили сообщение от группы Telehooper, игнорируем.

			return
			# TODO

		if msg.out:
			await self.onNewOutcomingMessage(user, msg)
		else:
			await self.onNewIncomingMessage(user, msg)

	async def onNewIncomingMessage(self, user: "TelehooperUser", msg: Message):
		await super().onNewIncomingMessage(user)

		FROM_USER = msg.peer_id < 2000000000
		FROM_CONVO = msg.peer_id >= 2000000000

		# Если у пользователя есть группа-диалог, то сообщение будет отправлено именно туда:
		dialogue = await self.telehooper_bot.getDialogueGroupByServiceDialogueID(msg.peer_id)

		# Если такая диалог-группа не была найдена, то ничего не делаем.
		if not dialogue:
			return

		# Обработаем вложения:
		fileAttachments: List[Utils.File] = []
		for vkAttachment in msg.attachments or []:
			TYPE = vkAttachment.type.value

			# Смотрим, какой тип вложения получили:
			if TYPE == "photo":
				# Фотография.
				URL: str = cast(str, vkAttachment.photo.sizes[-5].url) # type: ignore

				fileAttachments.append(Utils.File(URL))
			elif TYPE == "audio_message":
				# Голосовое сообщение.
				URL: str = vkAttachment.audio_message.link_ogg # type: ignore

				fileAttachments.append(Utils.File(URL, "voice"))
			elif TYPE == "sticker":
				# Стикер.
				URL: str = vkAttachment.sticker.animation_url or vkAttachment.sticker.images[-1].url # type: ignore

				fileAttachments.append(Utils.File(URL, "sticker"))
			elif TYPE == "video":
				# Видео.
				# Так как ВК не дают простого метода получения прямой
				# ссылки на видео, приёдтся использовать закрытый API:

				async with aiohttp.ClientSession() as client:
					async with client.post("https://api.vk.com/method/video.get",
						data={
							"videos": f"{vkAttachment.video.owner_id}_{vkAttachment.video.id}_{vkAttachment.video.access_key}", # type: ignore
							"access_token": await user.vkAPI.token_generator.get_token(),
							"v": "5.131"
						}
					) as response:
						res = (await response.json())["response"]["items"][-1]["files"]

						URL: str = cast(
							str, 
							Utils.getFirstAvailableValueFromDict(
								res, 
								"mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240", "mp4_144"
							)
						)

						fileAttachments.append(Utils.File(URL, "video"))

		# Ответ на сообщение:
		replyMessageID = None
		if msg.reply_message:
			res = self.getMessageDataByServiceMID(user, msg.reply_message.id or 0)
			if res:
				replyMessageID = res.telegramMID

		# Если сообщение из беседы, то добавляем имя:
		msgPrefix = ""
		if FROM_CONVO:
			# Получаем имя отправителя:

			sender = await msg.get_user()
			msgPrefix = (sender.first_name or "") + " " + (sender.last_name or "") + ": "

		# Отправляем сообщение и сохраняем в ДБ:
		telegramMessage = cast(aiogram.types.Message, await self.telehooper_bot.sendMessage(
			user=user,
			text=msgPrefix + (msg.text.replace("<", "&lt;") or "<i>ошибка: пустой текст у сообщения. возможно, в сообщении неподдерживаемый тип?</i>"),
			chat_id=dialogue.group.id,
			attachments=fileAttachments,
			reply_to=replyMessageID,
			return_only_first_element=True
		))

		self.telehooper_bot.vkAPI = cast("VKTelehooperAPI", self.telehooper_bot.vkAPI)
		self.telehooper_bot.vkAPI.saveMessageID(
			user,
			telegramMessage.message_id,
			msg.id,
			dialogue.group.id,
			msg.chat_id,
			False
		)

	async def onNewOutcomingMessage(self, user: "TelehooperUser", msg: Message):
		await super().onNewOutcomingMessage(user)

	async def onMessageEdit(self, user: "TelehooperUser", msg):
		await super().onMessageEdit(user)

		# Получаем ID сообщения в Telegram:

		MSGID = msg.object[1]
		MSGTEXT = msg.object[6]
		MSGCHATID = msg.object[3]

		res = self.getMessageDataByServiceMID(user, MSGID)
		if not res:
			return

		# Сообщение найдено, проверяем, кто его отправил.
		# Если было получено с Telegram, то не редактируем.
		if res.sentViaTelegram:
			return

		# В ином случае, редактируем:
		await self.telehooper_bot.editMessage(user, MSGTEXT.replace("<", "&lt;"), res.telegramDialogueID, res.telegramMID)

	async def onMessageDelete(self, user: "TelehooperUser", msg):
		await super().onMessageDelete(user)

		# Получаем ID сообщения в Telegram:

		MSGID = msg.object[1]
		MSGCHATID = msg.object[3]

		res = self.getMessageDataByServiceMID(user, MSGID)
		if not res:
			return

		# Сообщение найдено, проверяем, кто его отправил.
		# Если было получено с Telegram, то не удаляем.
		if res.sentViaTelegram:
			return

		# В ином случае, удаляем:
		await self.telehooper_bot.deleteMessage(user, res.telegramDialogueID, res.telegramMID)

	async def onDialogueActivity(self, user: "TelehooperUser", chat_id: int, activity_type: Literal["voice", "file", "photo", "typing", "video"] = "typing"):
		await super().onDialogueActivity(user)

		# Ищем диалог в Telegram:
		res = await self.getDialogueGroupByServiceDialogueID(chat_id)
		if not res:
			return

		telegram_activiy = {
			"typing": "typing",
			"photo": "upload_photo", 
			"video": "record_video", 
			"voice": "record_voice", 
			"file": "upload_document", 
			"video": "record_video_note", 
		}

		activity = telegram_activiy.get(activity_type, "typing")

		await self.telehooper_bot.startDialogueActivity(res.group.id, activity) # type: ignore

	async def _sendSuccessfulConnectionMessage(self, user: "TelehooperUser", connect_via_password: bool = False):
		space = "&#12288;" # Символ пробела, который не удаляется при отправке сообщения ВКонтакте.
		userInfoData = f"{space}• Имя: {user.TGUser.full_name}.\n"

		if user.TGUser.username:
			userInfoData += f"{space}• Никнейм в Telegram: {user.TGUser.username}.\n"
			userInfoData += f"{space}• Ссылка: https://t.me/{user.TGUser.username}​.\n"

		userInfoData += f"{space}• Авторизация была произведена через " + ("пароль" if connect_via_password else f"VK ID") + ".\n"

		await user.vkAPI.messages.send(
			user.APIstorage.vk.accountInfo.id, # type: ignore 
			random_id=Utils.generateVKRandomID(), 
			message=f"""⚠️ ВАЖНАЯ ИНФОРМАЦИЯ ⚠️ {space * 15}
Привет! 🙋
Если ты видишь это сообщение, то в таком случае значит, что Telegram-бот под названием «Telehooper» был успешно подключён к твоей странице ВКонтакте. Пользователь, который подключился к вашей странице ВКонтакте сумеет делать следующее:
{space}• Читать все получаемые и отправляемые сообщения.
{space}• Отправлять сообщения.
{space}• Смотреть список диалогов.
{space}• Просматривать список твоих друзей, отправлять им сообщения.
⚠ Если подключал бота не ты, то срочно {"в настройках подключённых приложений (https://vk.com/settings?act=apps) отключи приложение «Kate Mobile», либо же " if connect_via_password else "настройках «безопасности» (https://vk.com/settings?act=security) нажми на кнопку «Отключить все сеансы», либо же "}в этот же диалог пропиши команду «logoff», (без кавычек) и если же тут появится сообщение о успешном отключении, то значит, что бот был отключён. После отключения срочно меняй пароль от ВКонтакте, поскольку произошедшее значит, что кто-то сумел войти в твой аккаунт ВКонтакте, либо же ты забыл выйти с чужого компьютера!

Информация о пользователе, который подключил бота к твоей странице:
{userInfoData}
Если же это был ты, то волноваться незачем, и ты можешь просто проигнорировать всю предыдущую часть сообщения.

ℹ️ В этом диалоге можно делать следующее для управления Telehooper'ом; все команды прописываются без «кавычек»:
{space}• Проверить, подключён ли Telehooper: «test».
{space}• Отправить тестовое сообщение в Telegram: «ping».
{space}• Отключить аккаунт ВКонтакте от Telehooper: «logoff».""")

		# Пытаемся отправить оповестительное сообщение в ВК-группу:
		await asyncio.sleep(1)
		try:
			notifier_group_id = abs(int(os.environ["VKBOT_NOTIFIER_ID"]))

			if notifier_group_id > 0:
				await user.vkAPI.messages.send(-notifier_group_id, Utils.generateVKRandomID(), message="(это автоматическое сообщение, не обращай на него внимание.)\n\ntelehooperSuccessAuth")
		except:
			logger.warning(f"Не удалось отправить опциональное сообщение об успешной авторизации бота в ВК. Пожалуйста, проверьте настройку \"VKBOT_NOTIFIER_ID\" в .env файле. (текущее значение: {os.environ.get('VKBOT_NOTIFIER_ID')})")

	async def _saveConnectedUserToDB(self, user: "TelehooperUser", token: str, connect_via_password: bool = False):
		# Получаем базу данных:
		DB = getDefaultCollection()

		# Сохраняем информацию о авторизации:
		DB.update_one(
			{
				"_id": user.TGUser.id
			},

			{"$set": {
				"_id": user.TGUser.id,
				"TelegramUserID": user.TGUser.id,
				"IsAwareOfDialogueConversionConditions": False,
				"Services": {
					"VK": {
						"Auth": True,
						"IsAuthViaPassword": connect_via_password,
						"AuthDate": datetime.datetime.now(),
						"Token": Utils.encryptWithEnvKey(token),
						"ID": user.APIstorage.vk.accountInfo.id, # type: ignore
						"DownloadImage": await self._getDefaultDownloadingImage(user),
						"ServiceToTelegramMIDs": []
					}
				}
			}},

			upsert=True
		)

	async def _getDefaultDownloadingImage(self, user: "TelehooperUser") -> None | str:
		"""
		Выдаёт строку вида "photo123_456" которую можно использовать как attachment во время загрузки.
		"""

		DB = getDefaultCollection()
		
		res = DB.find_one({"_id": user.TGUser.id})

		if not res:
			return None

		vkService = res["Services"]["VK"]
		if not vkService.get("DownloadImage"):
			vkService["DownloadImage"] = await vkbottle.PhotoMessageUploader(user.vkAPI).upload("resources/downloadImage.png")

			DB.update_one(
				{
					"_id": user.TGUser.id
				}, 
				
				{
					"$set": {
						"Services.VK.DownloadImage": vkService["DownloadImage"]
					}
				}
			)

		return vkService["DownloadImage"]

	async def startDialogueActivity(self, user: "TelehooperUser", chat_id: int | str, action: Literal["audiomessage", "file", "photo", "typing", "video"]):
		await super().startDialogueActivity(user)

		await user.vkAPI.messages.set_activity(int(chat_id), action)

	async def sendMessage(self, user: "TelehooperUser", message: str, chat_id: int | None = None, msg_id_to_reply: int | None = None, attachmentsFile: Utils.File | List[Utils.File] | None = None, silent: bool = False, allow_creating_temp_message: bool = True, start_chat_activities: bool = True):
		await super().sendMessage(user)

		async def _chatAction(chat_id: int, action: Literal["audiomessage", "file", "photo", "typing", "video"] = "typing"):
			"""
			Выполняет действие в чати по типу печати.
			"""

			if not start_chat_activities:
				return

			await self.startDialogueActivity(user, chat_id, action)

		attachmentStr: List[str] = []

		if message is None:
			message = ""

		if chat_id is None:
			chat_id = user.APIstorage.vk.accountInfo.id

		tempMessageID: None | int = None
		if attachmentsFile:
			# Я не хотел делать отдельный кейс когда переменная не является листом, поэтому:
			if not isinstance(attachmentsFile, list):
				attachmentsFile = [attachmentsFile]

			# Проверяем, если у нас >= 2 вложений, то мы должны отправить временное
			# сообщение, и потом в него добавить вложения.
			if allow_creating_temp_message and len(attachmentsFile) >= 2:
				tempPhotoAttachment = await self._getDefaultDownloadingImage(user)
				assert tempPhotoAttachment is not None, "Не удалось получить временное изображение для вложений."

				tempMessageID = await user.vkAPI.messages.send(
					peer_id=chat_id, 
					random_id=Utils.generateVKRandomID(), 
					message=f"{message}\n\n(пожалуйста, дождись загрузки всех {len(attachmentsFile)} вложений, они появятся в этом сообщении.)", 
					reply_to=msg_id_to_reply, 
					attachment=(tempPhotoAttachment + ",") * len(attachmentsFile)
				)

			for index, file in enumerate(attachmentsFile):
				# attachment является типом Utils.File, но иногда он бывает не готовым к использованию,
				# т.е., он не имеет поля bytes, к примеру. Поэтому я сделаю дополнительную проверку:
				if not file.ready:
					await file.parse()

				assert file.bytes is not None, "attachment.bytes is None"

				# Окончательно загружаем файл на сервера ВК:
				uploadedAttachment: str
				uploadRes: str | None = None
				if file.type == "photo":
					await _chatAction(chat_id, "photo")
					uploadRes = await vkbottle.PhotoMessageUploader(user.vkAPI).upload(file.bytes) # type: ignore
				elif file.type == "voice":
					await _chatAction(chat_id, "audiomessage")
					uploadRes = await vkbottle.VoiceMessageUploader(user.vkAPI).upload(title="voice message title?", file_source=file.bytes) # type: ignore
				elif file.type == "sticker":
					await _chatAction(chat_id, "photo")
					
					# Следующий код необходим для обхода запрета ВК для отправки графити:
					# https://vk.com/wall-1_395554

					# Отредактируем размер стикера:
					try:
						img = Image.open(io.BytesIO(file.bytes))
					except:
						raise Exception("Animated stickers aren't supported yet.")

					HEIGHT = img.height
					WIDTH = img.width
					
					HEIGHT_EDITED = int(Utils.clamp(HEIGHT, 32, 128))
					WIDTH_EDITED = int(WIDTH / (HEIGHT / Utils.clamp(HEIGHT, 32, 128)))
					# С шириной изображения мы делаем некоторые хитрости, что бы
					# стикер в некоторых случаях не был сильно растянут, 
					# или наоборот сжат.

					img = img.resize(
						(
							WIDTH_EDITED,
							HEIGHT_EDITED
						)
					)
					img_bytes = io.BytesIO()
					img.save(img_bytes, format='PNG')
					img_bytes = img_bytes.getvalue()
					del img

					uploadUrl = (await vkbottle.DocUploader(user.vkAPI).get_server(type="graffiti"))["upload_url"]
					async with aiohttp.ClientSession() as session:
						data = aiohttp.FormData()
						data.add_field(
							"file", img_bytes, 
							filename="graffiti.png", 
							content_type="image/png"
						)

						async with session.post(uploadUrl, data=data) as response:
							response = await response.json()

							res = cast(MessagesGraffiti, (await user.vkAPI.docs.save((response)["file"])).graffiti)
							uploadRes = f"doc{res.owner_id}_{res.id}"
						
				else:
					raise Exception(f"Неподдерживаемый тип: {file.type}")

				assert uploadRes is not None, "uploadRes is None"

				uploadedAttachment = uploadRes
				del uploadRes

				# Добавляем строку вида "photo123_456" в массив:
				attachmentStr.append(uploadedAttachment)


				# Через каждый второй файл делаем sleep:
				if index % 2 == 1:
					await asyncio.sleep(0.5)
		else:
			# У нас нет никаких вложений:
			await _chatAction(chat_id, "typing")

		# Если у нас было создано временное сообщение с изображениями, то мы должны
		# его отредактировать, что бы вставить загруженные файлы.
		if allow_creating_temp_message and tempMessageID:
			await user.vkAPI.messages.edit(
				peer_id=chat_id, 
				message=message, 
				message_id=tempMessageID, 
				attachment=",".join(attachmentStr)
			)

			return tempMessageID
		else:
			# В ином случае, просто отправляем готовое сообщение
			# со всеми вложениями.

			return await user.vkAPI.messages.send(
				peer_id=chat_id, 
				random_id=Utils.generateVKRandomID(), 
				message=message, 
				reply_to=msg_id_to_reply, 
				attachment=",".join(attachmentStr),
				silent=silent
			)

			return res

	async def editMessage(self, user: "TelehooperUser", message: str, chat_id: int, message_id: int, attachments: str = ""):
		await super().editMessage(user)

		return await user.vkAPI.messages.edit(peer_id=chat_id, message_id=message_id, message=message, attachment=attachments)

	async def deleteMessage(self, user: "TelehooperUser", chat_id: int, message_id: int, delete_for_everyone: bool = False):
		await super().deleteMessage(user)

		return await user.vkAPI.messages.delete(peer_id=chat_id, message_id=message_id, delete_for_all=delete_for_everyone)

	def getMessageDataByServiceMID(self, user: "TelehooperUser", service_message_id: int | str) -> None | MappedMessage:
		return super().getMessageDataByServiceMID(user, "VK", service_message_id)

	def getMessageDataByTelegramMID(self, user: "TelehooperUser", telegram_message_id: int | str) -> None | MappedMessage:
		return super().getMessageDataByTelegramMID(user, "VK", telegram_message_id)

class VKDialogue:
	"""
	Класс, отображающий диалог ВК; это может быть диалог с пользователем, группой (ботом), или с беседой.
	"""

	_dialogue: Any
	_extended: Any
	_type: str

	isUser: bool
	isGroup: bool
	isConversation: bool
	isSelf: bool

	firstName: str
	lastName: str
	fullName: str
	username: str
	photoURL: str
	ID: int
	absID: int
	domain: str
	isPinned: bool
	isMale: bool


	def __init__(self, dialogue: MessagesConversationWithMessage, extended_info: UsersUserFull | GroupsGroupFull | None, self_user_id: int | None) -> None:
		self._dialogue = dialogue
		self._extended = extended_info
		self._type = dialogue.conversation.peer.type.value

		self.isUser = self._type == "user"
		self.isGroup = self._type == "group"
		self.isConversation = self._type == "chat"
		self.isSelf = self.isUser and self._dialogue.conversation.peer.id == self_user_id

		assert self.isUser or self.isGroup or self.isConversation, f"Неизвестный тип диалога: {self._type}"

		self.isPinned = self._dialogue.conversation.sort_id.major_id > 0


		if self.isUser:
			if self.isSelf:
				self.firstName = "Избранное"
				self.lastName = ""
				self.fullName = "Избранное"
			else:
				self.firstName = self._extended.first_name
				self.lastName = self._extended.last_name
				self.fullName = f"{self.firstName} {self.lastName}"

			self.username = self._extended.domain
			self.photoURL = self._extended.photo_100
			self.ID = self._extended.id
			self.absID = self.ID
			self.domain = self._extended.screen_name
			self.isMale = self._extended.sex == 2
		elif self.isGroup:
			self.firstName = self._extended.name
			self.lastName = ""
			self.fullName = self.firstName
			self.username = self._extended.screen_name
			self.photoURL = self._extended.photo_100
			self.ID = -self._extended.id
			self.absID = abs(self.ID)
			self.domain = self._extended.screen_name
			self.isMale = True
		else:
			self.firstName = self._dialogue.conversation.chat_settings.title
			self.lastName = ""
			self.fullName = self.firstName
			self.username = ""
			self.ID = self._dialogue.conversation.peer.id
			self.absID = self.ID - 2000000000
			self.domain = ""
			self.isMale = True

			_photo = self._dialogue.conversation.chat_settings.photo
			if _photo:
				self.photoURL = Utils.getFirstAvailableValueFromClass(_photo, "photo_max_orig", "photo_max", "photo_400_orig", "photo_200_orig", "photo_200", default="https://vk.com/images/camera_400.png") # type: ignore

	def __str__(self) -> str:
		return f"<VKDialogue id{self.ID}>"

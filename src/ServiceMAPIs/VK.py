# coding: utf-8

from __future__ import annotations

import asyncio
import datetime
import os
from asyncio import Task
from typing import TYPE_CHECKING, Any, List, Literal
from vkbottle.user import Message

import aiogram
import Utils
import vkbottle
from Consts import AccountDisconnectType
from DB import getDefaultCollection
from loguru import logger
from vkbottle.tools.dev.mini_types.base.message import BaseMessageMin
from vkbottle_types.responses.groups import GroupsGroupFull
from vkbottle_types.responses.messages import MessagesConversationWithMessage
from vkbottle_types.responses.users import UsersUserFull

from .Base import BaseTelehooperAPI

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
		fullUserInfo = await vkAccountAPI.users.get(user_ids=[accountInfo.id])

		# Если мы дошли до этого момента, значит, что страница подключена, и токен верный.
		
		user.APIstorage.vk.accountInfo = accountInfo
		user.APIstorage.vk.fullUserInfo = fullUserInfo[0]
		user.vkAPI = vkAccountAPI
		user.vkUser = vkbottle.User(token)

		# Запускаем longpoll:
		await self.runPolling(user)

		# Вызываем метод API бота:
		if call_onSuccessfulConnection_method:
			await self.onSuccessfulConnection(user)

	async def disconnect(self, user: "TelehooperUser", reason: int = AccountDisconnectType.INITIATED_BY_USER):
		await super().disconnect(user)

		print("Должен был произойти дисконнект юзера, юху!")
		self.stopPolling(user)

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
			
		# user.vkUser.on.raw_event(vkbottle.UserEventType.MESSAGE_EDIT)(self.onMessageEdit) # type: ignore
		# user.vkUser.on.raw_event(vkbottle.UserEventType.DIALOG_TYPING_STATE)(self.onChatTypingState) # type: ignore
		# user.vkUser.on.raw_event(vkbottle.UserEventType.CHAT_TYPING_STATE)(self.onChatTypingState) # type: ignore
		# user.vkUser.on.raw_event(vkbottle.UserEventType.CHAT_VOICE_MESSAGE_STATES)(self.onChatTypingState) # type: ignore
		# user.vkUser.on.raw_event(vkbottle.UserEventType.FILE_UPLOAD_STATE)(self.onChatTypingState) # type: ignore
		# user.vkUser.on.raw_event(vkbottle.UserEventType.VIDEO_UPLOAD_STATE)(self.onChatTypingState) # type: ignore
		# user.vkUser.on.raw_event(vkbottle.UserEventType.PHOTO_UPLOAD_STATE)(self.onChatTypingState) # type: ignore

		# Создаём Polling-задачу:
		user.APIstorage.vk.pollingTask = asyncio.create_task(user.vkUser.run_polling(), name=f"VK Polling, id{user.APIstorage.vk.accountInfo.id}") # type: ignore

		return user.APIstorage.vk.pollingTask

	def stopPolling(self, user: "TelehooperUser") -> None:
		"""
		Останавливает Polling.
		"""

		if not user.APIstorage.vk.pollingTask:
			return

		user.APIstorage.vk.pollingTask.cancel() # type: ignore

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
		Возвращает диалог по его ID.
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

	def saveMessageID(self, user: "TelehooperUser", telegram_message_id: int | str, service_message_id: int | str, telegram_dialogue_id: int | str, service_dialogue_id: int | str, sent_via_telegram: bool) -> None:
		"""Сохраняет ID сообщения в базу."""

		# Сохраняем ID сообщения в ДБ:
		DB = getDefaultCollection()
		DB.update_one({"_id": user.TGUser.id}, {
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
		self.telehooper_bot.saveLatestMessageID(telegram_dialogue_id, telegram_message_id, service_message_id)

	async def onNewMessage(self, user: "TelehooperUser", msg: Message):
		await super().onNewMessage(user)

		FROM_USER = msg.peer_id < 2000000000
		FROM_CONVO = msg.peer_id >= 2000000000

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

		if msg.out:
			# Мы получили сообщение, отправленное самим пользователем, игнорируем.

			return

		if abs(msg.peer_id) == int(os.environ.get("VKBOT_NOTIFIER_ID", 0)):
			# Мы получили сообщение от группы Telehooper, игнорируем.

			return
			# TODO

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
				URL: str = vkAttachment.photo.sizes[-5].url # type: ignore

				fileAttachments.append(Utils.File(URL))
			elif TYPE == "audio_message":
				# Голосовое сообщение.
				URL: str = vkAttachment.audio_message.link_ogg # type: ignore

				fileAttachments.append(Utils.File(URL, "voice"))
			elif TYPE == "sticker":
				# Стикер.
				URL: str = vkAttachment.sticker.animation_url or vkAttachment.sticker.images[-1].url # type: ignore

				fileAttachments.append(Utils.File(URL, "sticker"))

		# Ответ на сообщение:
		# TODO
		replyMessageID = None
		if msg.reply_message:
			# res = self.telehooper_bot.getMessageDataByServiceMID(msg.reply_message.id or 0)
			# if res:
			# 	replyMessageID = res.telegramMID
			pass

		# Если сообщение из беседы, то добавляем имя:
		msgPrefix = ""
		if FROM_CONVO:
			# Получаем имя отправителя:

			# sender = await msg.get_user()
			# msgPrefix = (sender.first_name or "") + " " + (sender.last_name or "") + ": "
			pass

		# Отправляем сообщение и сохраняем в ДБ:
		telegramMessage = await self.telehooper_bot.send_message(
			user=user,
			text=msgPrefix + (msg.text or "<i>ошибка: пустой текст у сообщения. возможно, в сообщении неподдерживаемый тип?</i>"),
			chat_id=dialogue.group.id,
			attachments=fileAttachments,
			reply_to=replyMessageID,
			return_only_first_element=True
		)

		self.telehooper_bot.save(
			telegramMessage.message_id, # type: ignore
			msg.id,
			dialogue.group.id,
			msg.chat_id,
			False
		)

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
						"Token": token,
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
			vkService["DownloadImage"] = await vkbottle.PhotoMessageUploader(user.vkAPI).upload("downloadImage.png")
			DB.update_one({"_id": user.TGUser.id}, {"$set": {"Services.VK.DownloadImage": vkService["DownloadImage"]}})

		return vkService["DownloadImage"]

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

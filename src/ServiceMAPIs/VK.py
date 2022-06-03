# coding: utf-8

from __future__ import annotations

import asyncio
import datetime
import io
import logging
import os
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

import aiogram
import vkbottle
import vkbottle_types
import vkbottle_types.responses.users
from Consts import AccountDisconnectType
from DB import getDefaultCollection
from MiddlewareAPI import MappedMessage, MiddlewareAPI, TelehooperUser
from Utils import generateVKRandomID, getFirstAvailableValueFromClass
from vkbottle.user import Message
from vkbottle_types.responses.groups import GroupsGroupFull
from vkbottle_types.responses.messages import MessagesConversationWithMessage
from vkbottle_types.responses.users import UsersUserFull
import Utils
import PIL
from PIL import Image

logger = logging.getLogger("VKMAPI") # TODO: Заменить этот logger на логгер внутри класса.


if TYPE_CHECKING:
	from TelegramBot import Telehooper


"""
MiddlewareAPI для ВКонтакте.
"""

class VKMiddlewareAPI(MiddlewareAPI):
	"""
	Middleware API для ВКонтакте. Расширяет класс MiddlewareAPI.
	"""

	pollingTask: asyncio.Task | None
	isPollingRunning: bool
	vkAccount: VKAccount
	vkAPI: vkbottle.API

	def __init__(self, user: "TelehooperUser", bot: "Telehooper") -> None:
		super().__init__(user, bot)

		self.pollingTask = None
		self.isPollingRunning = False
		self.vkAccount = self.user.vkAccount
		self.vkAPI = self.vkAccount.vkAPI


	def runPolling(self) -> asyncio.Task:
		"""
		Запускает Polling для получения сообщений.
		"""

		if self.isPollingRunning:
			self.pollingTask

		@self.vkAccount.vkUser.error_handler.register_error_handler(vkbottle.VKAPIError[5])
		async def errorHandler(error: vkbottle.VKAPIError):
			# Если этот код вызывается, то значит, что пользователь отозвал разрешения ВК, и сессия была отозвана.

			# Отправляем различные сообщения о отключённом боте:
			await self.disconnectService(AccountDisconnectType.EXTERNAL)

		# Регестрируем события в ВК:
		self.vkAccount.vkUser.on.message()(self.onNewRecievedMessage)
		self.vkAccount.vkUser.on.raw_event(vkbottle.UserEventType.MESSAGE_EDIT)(self.onMessageEdit) # type: ignore
		self.vkAccount.vkUser.on.raw_event(vkbottle.UserEventType.DIALOG_TYPING_STATE)(self.onChatTypingState) # type: ignore

		# Создаём Polling-задачу:
		self.pollingTask = asyncio.create_task(self.vkAccount.vkUser.run_polling(), name=f"VK Polling, id{self.user.vkAccount.vkFullUser.id}")
		self.isPollingRunning = True

		return self.pollingTask

	def stopPolling(self) -> None:
		"""
		Останавливает Polling.
		"""

		if not self.isPollingRunning:
			return

		# Отключаем Task, используя следующий метод:
		# task.cancel() использовать нельзя из-за бага библиотеки vkbottle.
		#
		# https://github.com/vkbottle/vkbottle/issues/504
		self.user.vkAccount.vkUser.polling.stop = True # type: ignore (переменной нет в vkbottle_types)

		self.isPollingRunning = False

	async def sendServiceMessageOut(self, message: str, msg_id_to_reply: int | None = None) -> int:
		return await self.sendMessageOut(message, self.user.vkAccount.vkFullUser.id, msg_id_to_reply)

	async def sendMessageOut(self, message: str, chat_id: int, msg_id_to_reply: int | None = None, attachmentsFile: Utils.File | List[Utils.File] | None = None, allow_creating_temp_message: bool = True) -> int:
		attachmentStr: List[str] = []

		# Небольшой багфикс:
		if message is None:
			message = ""

		tempMessageID: None | int = None
		if attachmentsFile:
			# Я не хотел делать отдельный кейс когда переменная не является листом, поэтому:
			if not isinstance(attachmentsFile, list):
				attachmentsFile = [attachmentsFile]

			# Проверяем, если у нас >= 2 вложений, то мы должны отправить временное
			# сообщение, и потом в него добавить вложения.
			if allow_creating_temp_message and len(attachmentsFile) >= 2:
				tempPhotoAttachment = await self.vkAccount.getDefaultDownloadingImage()
				assert tempPhotoAttachment is not None, "Не удалось получить временное изображение для вложений."

				tempMessageID = await self.user.vkAccount.vkAPI.messages.send(peer_id=chat_id, random_id=generateVKRandomID(), message=f"{message}\n\n(пожалуйста, дождись загрузки всех {len(attachmentsFile)} вложений, они появятся в этом сообщении.)", reply_to=msg_id_to_reply, attachment=(tempPhotoAttachment + ",") * len(attachmentsFile))

			for index, file in enumerate(attachmentsFile):
				# attachment является типом Utils.File, но иногда он бывает не готовым к использованию,
				# т.е., он не имеет поля bytes, к примеру. Поэтому я сделаю дополнительную проверку:
				if not file.ready:
					await file.parse()

				assert file.bytes is not None, "attachment.bytes is None"

				# Окончательно загружаем файл на сервера ВК:
				uploadedAttachment: str
				uploadRes: str | None = None
				if file.type == "photo" or file.type == "sticker":
					uploadRes = await vkbottle.PhotoMessageUploader(self.vkAPI).upload(file.bytes) # type: ignore
				elif False:
					# Спасибо ВК что ограничили доступ к отправки граффити <3

					uploadRes = await vkbottle.GraffitiUploader(self.vkAPI).upload(title="стикер", file_source=open("downloadImage.png", "rb").read()) # type: ignore


				assert uploadRes is not None, "uploadRes is None"

				uploadedAttachment = uploadRes
				del uploadRes

				# Добавляем строку вида "photo123_456" в массив:
				attachmentStr.append(uploadedAttachment)


				# Через каждый второй файл делаем sleep:
				if index % 2 == 1:
					await asyncio.sleep(0.5)

		if allow_creating_temp_message and tempMessageID:
			await self.vkAPI.messages.edit(peer_id=chat_id, message=message, message_id=tempMessageID, attachment=",".join(attachmentStr))
			return tempMessageID
		else:
			return await self.vkAPI.messages.send(peer_id=chat_id, random_id=generateVKRandomID(), message=message, reply_to=msg_id_to_reply, attachment=",".join(attachmentStr))

	async def editMessageOut(self, message: str, chat_id: int, message_id: int) -> int:
		return await self.user.vkAccount.vkAPI.messages.edit(peer_id=chat_id, message_id=message_id, message=message)

	async def onNewRecievedMessage(self, msg: Message) -> None:
		"""
		Обработчик входящих/исходящих сообщений полученных из ВКонтакте.
		"""

		if self.user.vkAccount.vkFullUser is None:
			# Полная информация о пользователе ещё не была получена.

			return

		if msg.peer_id == self.user.vkAccount.vkFullUser.id:
			# Мы получили сообщение в "Избранном", обрабатываем сообщение как команду,
			# но боту в ТГ ничего не передаём.
			tg_message = await self._commandHandler(msg)

			if tg_message and isinstance(tg_message, aiogram.types.Message):
				# Сообщение в Телеграм.

				self.saveMessageID(tg_message.message_id, msg.message_id, tg_message.chat.id, msg.chat_id, False)


			return

		if msg.out:
			# Мы получили сообщение, отправленное самим пользователем, игнорируем.

			return

		if abs(msg.peer_id) == int(os.environ.get("VKBOT_NOTIFIER_ID", 0)):
			# Мы получили сообщение от группы Telehooper, игнорируем.

			return

		# Если у пользователя есть группа-диалог, то сообщение будет отправлено именно туда:
		dialogue = await self.bot.getDialogueGroupByServiceDialogueID(msg.peer_id)
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

		# Reply сообщения:
		replyMessageID = None
		if msg.reply_message:
			res = self.getMessageDataByServiceMID(msg.reply_message.id or 0)
			if res:
				replyMessageID = res.telegramMID

		self.saveMessageID(
			(await self.sendMessageIn(text=msg.text, chat_id=dialogue.group.id, attachments=fileAttachments, reply_to=replyMessageID, return_only_first_element=True)).message_id, # type: ignore
			msg.id,
			dialogue.group.id,
			msg.chat_id,
			False
		)

	async def onMessageEdit(self, msg) -> None:
		# Получаем ID сообщения в Telegram:

		MSGID = msg.object[1]
		MSGTEXT = msg.object[6]
		MSGCHATID = msg.object[3]

		# TODO: Добавить проверку, кто именно редактировал сообщение.

		res = self.getMessageDataByServiceMID(MSGID)
		if res:
			# Сообщение найдено, проверяем, кто его отправил.
			# Если было получено с Telegram, то не редактируем.
			if res.sentViaTelegram:
				return

			# В ином случае, редактируем:
			await self.editMessageIn(MSGTEXT + "ㅤㅤㅤ<i>изменено</i>", res.telegramDialogueID, res.telegramMID)

	async def onChatTypingState(self, typing_object):
		CHAT_ID = typing_object.object[1]

		# Узнаём, диалог ли это:
		dialogue = await self.user.getDialogueGroupByServiceDialogueID(CHAT_ID)
		if not dialogue:
			return False

		# В ином случае, начинаем "печатать":
		await self.startChatActionStateIn(dialogue.group.id, "typing")

	async def disconnectService(self, disconnect_type: int = AccountDisconnectType.INITIATED_BY_USER, send_service_messages: bool = True) -> None:
		"""
		Выполняет определённые действия при отключении сервиса/аккаунта от бота.
		"""

		await super().disconnectService(disconnect_type, send_service_messages)

		# Останавливаем Polling:
		self.stopPolling()

		if send_service_messages:
			# Мы должны отправить сообщения в самом сервисе о отключении:
			await self.user.vkAccount.vkAPI.messages.send(self.user.vkAccount.vkFullUser.id, random_id=generateVKRandomID(), message="ℹ️ Ваш аккаунт ВКонтакте был успешно отключён от бота «Telehooper».\n\nНадеюсь, что ты в скором времени вернёшься 🥺")

		self.user.isVKConnected = False
		self.vkAccount = None # type: ignore
		self.vkAPI = None # type: ignore

	def getMessageIDByTelegramMID(self, telegram_message_id: int | str) -> None | MappedMessage:
		return self._getMessageDataByKeyname("TelegramMID", telegram_message_id)

	def getMessageDataByServiceMID(self, vk_message_id: int | str) -> None | MappedMessage:
		return self._getMessageDataByKeyname("ServiceMID", vk_message_id)

	def _getMessageDataByKeyname(self, key: str, value: int | str):
		# Получаем из ДБ информацию:
		DB = getDefaultCollection()
		res = DB.find_one({"_id": self.user.TGUser.id})
		if res:
			res = res["Services"]["VK"]["ServiceToTelegramMIDs"]

			for r in res:
				if r[key] == str(value):
					TELEGRAMMID = int(r["TelegramMID"])
					SERVICEMID = int(r["ServiceMID"])
					TELEGRAMDIALOGUEID = int(r["TelegramDialogueID"])
					SERVICEDIALOGUEID = int(r["ServiceDialogueID"])
					VIATELEGRAM = bool(r["ViaTelegram"])

					return MappedMessage(TELEGRAMMID, SERVICEMID, TELEGRAMDIALOGUEID, SERVICEDIALOGUEID, VIATELEGRAM)

		return None



	async def _commandHandler(self, msg: Message) -> int | aiogram.types.Message:
		"""
		Обработчик команд, отправленных внутри сервиса, т.е., например, в чате "Избранное" в ВК.
		"""

		async def _commandRecieved(msg: Message):
			await self.user.vkAccount.vkAPI.messages.edit(self.user.vkAccount.vkFullUser.id, "✅ " + msg.text, message_id=msg.id)

		if msg.text.startswith("logoff"):
			# Выходим из аккаунта:
			await _commandRecieved(msg)

			await self.disconnectService(AccountDisconnectType.EXTERNAL)

			# Отправляем сообщения:
			await self.sendServiceMessageOut("ℹ️ Ваш аккаунт ВКонтакте был успешно отключён от бота «Telehooper».", msg.id)
			return 0
		elif msg.text.startswith("test"):
			await _commandRecieved(msg)

			await self.sendServiceMessageOut("✅ Telegram-бот «Telehooper» работает!", msg.id)
			return 0
		elif msg.text.startswith("ping"):
			await _commandRecieved(msg)

			return await self.sendServiceMessageIn("[<b>ВКонтакте</b>] » Проверка связи! 👋")
		else:
			# Неизвестная команда.

			return 0

class VKAccount:
	"""
	Класс, отображающий аккаунт ВКонтакте пользователя.
	"""

	vkToken: str

	user: TelehooperUser

	authViaPassword: bool


	vkAPI: vkbottle.API
	vkFullUser: vkbottle_types.responses.users.UsersUserFull
	vkUser: vkbottle.User
	vkDialogues: List[VKDialogue]

	def __init__(self, vkToken: str, user: TelehooperUser, auth_via_password: bool = False) -> None:
		self.vkToken = vkToken

		self.user = user

		self.authViaPassword = auth_via_password


		self.vkAPI = vkbottle.API(self.vkToken)
		self.vkFullUser = None # type: ignore
		self.vkUser = vkbottle.User(self.vkToken)
		self.vkDialogues = [] # type: ignore

	async def initUserInfo(self) -> vkbottle_types.responses.users.UsersUserFull:
		"""
		Обращается к API ВКонтакте, чтобы получить информацию о пользователе.
		"""

		# Получаем всю открытую информацию о пользователе.
		self.vkFullUser = (await self.vkAPI.users.get())[0]

		return self.vkFullUser

	async def postAuthInit(self) -> None:
		"""Действия, выполняемые после успешной авторизации пользоваля ВКонтакте: Отправляет предупредительные сообщения, и так далее."""

		space = "&#12288;" # Символ пробела, который не удаляется при отправке сообщения ВКонтакте.
		userInfoData = f"{space}• Имя: {self.user.TGUser.first_name}"

		if self.user.TGUser.last_name:
			userInfoData += " {self.telegramUser.last_name}"
		userInfoData += ".\n"

		if self.user.TGUser.username:
			userInfoData += f"{space}• Никнейм в Telegram: {self.user.TGUser.username}.\n"
			userInfoData += f"{space}• Ссылка: https://t.me/{self.user.TGUser.username}​.\n"

		userInfoData += f"{space}• Авторизация была произведена через " + ("пароль" if self.authViaPassword else f"VK ID") + ".\n"


		await self.vkAPI.messages.send(self.vkFullUser.id, random_id=generateVKRandomID(), message=f"""⚠️ ВАЖНАЯ ИНФОРМАЦИЯ ⚠️ {space * 15}

Привет! 🙋
Если ты видишь это сообщение, то в таком случае значит, что Telegram-бот под названием «Telehooper» был успешно подключён к твоей странице ВКонтакте. Пользователь, который подключился к вашей странице ВКонтакте сумеет делать следующее:
{space}• Читать все получаемые и отправляемые сообщения.
{space}• Отправлять сообщения.
{space}• Смотреть список диалогов.
{space}• Просматривать список твоих друзей, отправлять им сообщения.
⚠ Если подключал бота не ты, то срочно {"в настройках подключённых приложений (https://vk.com/settings?act=apps) отключи приложение «Kate Mobile», либо же " if self.authViaPassword else "настройках «безопасности» (https://vk.com/settings?act=security) нажми на кнопку «Отключить все сеансы», либо же "}в этот же диалог пропиши команду «logoff», (без кавычек) и если же тут появится сообщение о успешном отключении, то значит, что бот был отключён. После отключения срочно меняй пароль от ВКонтакте, поскольку произошедшее значит, что кто-то сумел войти в твой аккаунт ВКонтакте, либо же ты забыл выйти с чужого компьютера!
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
				await self.vkAPI.messages.send(-notifier_group_id, generateVKRandomID(), message="(это автоматическое сообщение, не обращай на него внимание.)\n\ntelehooperSuccessAuth")
		except:
			logger.warning(f"Не удалось отправить опциональное сообщение об успешной авторизации бота в ВК. Пожалуйста, проверьте настройку \"VKBOT_NOTIFIER_ID\" в .env файле. (текущее значение: {os.environ.get('VKBOT_NOTIFIER_ID')})")

		# Получаем базу данных:
		DB = getDefaultCollection()

		# Сохраняем информацию о авторизации:
		DB.update_one(
			{
				"_id": self.user.TGUser.id
			},
			{"$set": {
				"_id": self.user.TGUser.id,
				"TelegramUserID": self.user.TGUser.id,
				"IsAwareOfDialogueConversionConditions": False,
				"Services": {
					"VK": {
						"Auth": True,
						"IsAuthViaPassword": self.authViaPassword,
						"AuthDate": datetime.datetime.now(),
						"Token": self.vkToken,
						"ID": self.vkFullUser.id,
						"DownloadImage": await vkbottle.PhotoMessageUploader(self.vkAPI).upload("downloadImage.png"),
						"ServiceToTelegramMIDs": []
					}
				}
			}},
			upsert=True
		)

	async def getDefaultDownloadingImage(self) -> None | str:
		"""
		Выдаёт строку вида "photo123_456" которую можно использовать как attachment во время загрузки.
		"""

		DB = getDefaultCollection()
		res = DB.find_one({"_id": self.user.TGUser.id})
		if res:
			vkService = res["Services"]["VK"]
			if not vkService.get("DownloadImage"):
				vkService["DownloadImage"] = await vkbottle.PhotoMessageUploader(self.vkAPI).upload("downloadImage.png")
				DB.update_one({"_id": self.user.TGUser.id}, {"$set": {"Services.VK.DownloadImage": vkService["DownloadImage"]}})

			return vkService["DownloadImage"]

		return None

	async def checkAvailability(self, no_error: bool = False) -> bool:
		"""
		Делает тестовый API-запрос к VK для проверки доступности пользователя, и возвращяет тип Boolean.
		Слегка быстрее чем `initUserInfo()`, поскольку этот метод делает лишь один запрос.
		"""

		try:
			self.vkFullUser = (await self.vkAPI.users.get())[0]
		except Exception as error:
			if not no_error:
				raise(error)

			return False
		else:
			return True

	async def retrieveDialoguesList(self) -> List[VKDialogue]:
		"""
		Получает список всех диалогов пользователя, а так же кэширует их.
		"""

		convos = await self.vkAPI.messages.get_conversations(offset=0, count=200, extended=True)
		convos_extended_info = {}

		for group in convos.groups or {}:
			convos_extended_info.update({
				-group.id: group
			})

		for user in convos.profiles or {}:
			convos_extended_info.update({
				user.id: user
			})

		self.vkDialogues = []
		for convo in convos.items or {}:
			extended_info = convos_extended_info.get(convo.conversation.peer.id)

			self.vkDialogues.append(VKDialogue(convo, extended_info, self.vkFullUser.id)) # type: ignore


		return self.vkDialogues

	def getDialogueByID(self, dialogue_id: int) -> VKDialogue | None:
		"""
		Возвращает диалог по его ID.
		"""

		for dialogue in self.vkDialogues:
			if dialogue.ID == dialogue_id:
				return dialogue

		return None

	def __str__(self) -> str:
		return f"<VKAccount id{self.vkFullUser.id}>"

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


	def __init__(self, dialogue: MessagesConversationWithMessage, extended_info: UsersUserFull | GroupsGroupFull | None, self_user_id: Optional[int]) -> None:
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
				self.photoURL = getFirstAvailableValueFromClass(_photo, "photo_max_orig", "photo_max", "photo_400_orig", "photo_200_orig", "photo_200", default="https://vk.com/images/camera_400.png") # type: ignore

	def __str__(self) -> str:
		return f"<VKDialogue id{self.ID}>"

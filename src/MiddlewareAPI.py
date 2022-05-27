# coding: utf-8

# В этом файле находится middle-псевдо-API, благодаря которому различные 'коннекторы' могут соединяться с основым Telegram ботом.


from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import Any, List, Optional

import aiogram
import vkbottle
import vkbottle_types
import vkbottle_types.responses.account
import vkbottle_types.responses.users
from vkbottle.user import Message
from vkbottle_types.responses.groups import GroupsGroupFull
from vkbottle_types.responses.messages import MessagesConversationWithMessage
from vkbottle_types.responses.users import UsersUserFull

import Utils
from Consts import AccountDisconnectType
from DB import getDefaultCollection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from TelegramBot import Telehooper, DialogueGroup

logger = logging.getLogger(__name__)

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
		userInfoData = f"{space}* Имя: {self.user.TGUser.first_name}"

		if self.user.TGUser.last_name:
			userInfoData += " {self.telegramUser.last_name}"
		userInfoData += ".\n"

		if self.user.TGUser.username:
			userInfoData += f"{space}* Никнейм в Telegram: {self.user.TGUser.username}.\n"
			userInfoData += f"{space}* Ссылка: https://t.me/{self.user.TGUser.username}​.\n"

		userInfoData += f"{space}* Авторизация была произведена через " + ("пароль" if self.authViaPassword else f"VK ID") + ".\n"


		await self.vkAPI.messages.send(self.vkFullUser.id, random_id=Utils.generateVKRandomID(), message=f"""⚠️ ВАЖНАЯ ИНФОРМАЦИЯ ⚠️ {space * 15}

Привет! 🙋
Если ты видишь это сообщение, то в таком случае значит, что Telegram-бот под названием «Telehooper» был успешно подключён к твоей странице ВКонтакте. Пользователь, который подключился к вашей странице ВКонтакте сумеет делать следующее:
{space}• Читать все получаемые и отправляемые сообщения.
{space}• Отправлять сообщения.
{space}• Смотреть список диалогов.
{space}• Просматривать список твоих друзей, отправлять им сообщения.
⚠ Если подключал бота не ты, то срочно {"в настройках подключённых приложений (https://vk.com/settings?act=apps) отключи приложение «VK Messenger», либо же " if self.authViaPassword else "настройках «безопасности» (https://vk.com/settings?act=security) нажми на кнопку «Отключить все сеансы», либо же "}в этот же диалог пропиши команду «logoff», (без кавычек) и если же тут появится сообщение о успешном отключении, то значит, что бот был отключён. После отключения срочно меняй пароль от ВКонтакте, поскольку произошедшее значит, что кто-то сумел войти в твой аккаунт ВКонтакте, либо же ты забыл выйти с чужого компьютера!
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
				await self.vkAPI.messages.send(-notifier_group_id, Utils.generateVKRandomID(), message="(это автоматическое сообщение, не обращай на него внимание.)\n\ntelehooperSuccessAuth")
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
				"Services": {
					"VK": {
						"Auth": True,
						"IsAuthViaPassword": self.authViaPassword,
						"AuthDate": datetime.datetime.now(),
						"Token": self.vkToken,
						"ID": self.vkFullUser.id,
						"ServiceToTelegramMIDs": {} # "ID сообщения сервиса": "ID сообщения Telegram"
					}
				}
			}},
			upsert=True
		)

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
			self.absID = self.ID
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

class TelehooperUser:
	"""
	Класс, отображающий пользователя бота Telehooper: тут будут все подключённые сервисы.
	"""

	TGUser: aiogram.types.User
	bot: Telehooper

	vkAccount: VKAccount
	vkMAPI: VKMiddlewareAPI
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

		self.vkAccount = VKAccount(token, self, auth_via_password)
		await self.vkAccount.initUserInfo()

		await asyncio.sleep(0) # Спим 0 секунд, что бы последующий код не запускался до завершения кода выше.

		self.vkMAPI = VKMiddlewareAPI(self, self.bot, self.vkAccount)

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
		Отправляет сообщение пользователю Telegram.
		"""

		pass

	async def onNewSentMessage(self, messageText: str) -> None:
		"""
		Отправляет сообщение в сервис.
		"""

		pass

	async def sendMessageIn(self, message: str, chat_id: int) -> None:
		"""
		Отправляет сообщение в Telegram.
		"""

		await self.user.TGUser.bot.send_message(chat_id, message)

	async def sendMessageOut(self, message: str) -> None:
		"""
		Отправляет сообщение в сервисе.
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
					# TODO: Поменять этот текст:
					"⚠️ Аккаунт <b>«ВКонтакте»</b> был принудительно отключён от бота Telehooper; это действие было совершено <b>внешне</b>, напримёр, <b>отозвав все сессии в настройках безопасности аккаунта</b>."
					if (is_external) else
					"ℹ️ Аккаунт <b>«ВКонтакте»</b> был успешно отключён от Telehooper."
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
				"Services.VK.Token": None
			}},
			upsert=True
		)

	def __str__(self) -> str:
		return "<Base MiddlewareAPI class>"

class VKMiddlewareAPI(MiddlewareAPI):
	"""
	Middleware API для ВКонтакте. Расширяет класс MiddlewareAPI.
	"""

	pollingTask: asyncio.Task | None
	isPollingRunning: bool

	def __init__(self, user: TelehooperUser, bot: Telehooper, vkAccount: VKAccount) -> None:
		super().__init__(user, bot)

		self.pollingTask = None
		self.isPollingRunning = False


	def runPolling(self) -> asyncio.Task:
		"""
		Запускает Polling для получения сообщений.
		"""

		if self.isPollingRunning:
			self.pollingTask

		@self.user.vkAccount.vkUser.error_handler.register_error_handler(vkbottle.VKAPIError[5])
		async def errorHandler(error: vkbottle.VKAPIError):
			# Если этот код вызывается, то значит, что пользователь отозвал разрешения ВК, и сессия была отозвана.

			# Отправляем различные сообщения о отключённом боте:
			await self.disconnectService(AccountDisconnectType.EXTERNAL)

		self.user.vkAccount.vkUser.on.message()(self.onMessage)

		# Создаём Polling-задачу:
		self.pollingTask = asyncio.create_task(self.user.vkAccount.vkUser.run_polling(), name=f"VK Polling, id{self.user.vkAccount.vkFullUser.id}")

		self.isPollingRunning = True

		return self.pollingTask

	async def sendServiceMessageOut(self, message: str, msg_id_to_reply: int | None = None) -> int:
		return await self.sendMessageOut(message, self.user.vkAccount.vkFullUser.id, msg_id_to_reply)

	async def sendMessageOut(self, message: str, chat_id: int, msg_id_to_reply: int | None = None) -> int:
		return await self.user.vkAccount.vkAPI.messages.send(peer_id=chat_id, random_id=Utils.generateVKRandomID(), message=message, reply_to=msg_id_to_reply)

	async def _serviceCommandHandler(self, msg: Message) -> int | aiogram.types.Message:
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
	
	async def onMessage(self, msg: Message) -> None:
		"""
		Обработчик входящих/исходящих сообщений полученных из ВКонтакте.
		"""

		if self.user.vkAccount.vkFullUser is None:
			# Полная информация о пользователе ещё не была получена.

			return

		if msg.peer_id == self.user.vkAccount.vkFullUser.id:
			# Мы получили сообщение в "Избранном", обрабатываем сообщение как команду,
			# но боту в ТГ ничего не передаём.
			message = await self._serviceCommandHandler(msg)

			if message and isinstance(message, aiogram.types.Message):
				# Сообщение в Телеграм.

				self._saveMessageID(message.message_id, msg.message_id)


			return

		if msg.out:
			# Мы получили сообщение, отправленное самим пользователем, игнорируем.

			return

		if abs(msg.peer_id) == int(os.environ.get("VKBOT_NOTIFIER_ID", 0)):
			# Мы получили сообщение от группы Telehooper, игнорируем.

			return

		# Для тестирования, я просто буду отправлять сообщение в чат с пользователем,
		# но если у пользователя есть группа-диалог, то я отправлю сообщение именно туда:
		dialogue = await self.bot.getDialogueGroupByServiceDialogueID(abs(msg.peer_id))
		if dialogue:
			self._saveMessageID((await self.user.TGUser.bot.send_message(dialogue.group.id, msg.text)).message_id, msg.message_id)
			return

		# _saveMessageID((await self.user.TGUser.bot.send_message(self.user.TGUser.id, msg.text)).message_id)

	async def disconnectService(self, disconnect_type: int = AccountDisconnectType.INITIATED_BY_USER, send_service_messages: bool = True) -> None:
		"""
		Выполняет определённые действия при отключении сервиса/аккаунта от бота.
		"""

		await super().disconnectService(disconnect_type, send_service_messages)

		# Останавливаем Polling:
		self.stopPolling()

		if send_service_messages:
			# Мы должны отправить сообщения в самом сервисе о отключении:
			await self.user.vkAccount.vkAPI.messages.send(self.user.vkAccount.vkFullUser.id, random_id=Utils.generateVKRandomID(), message="ℹ️ Ваш аккаунт ВКонтакте был успешно отключён от бота «Telehooper».\n\nНадеюсь, что ты в скором времени вернёшься 🥺")
		
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

	def _saveMessageID(self, telegram_message_id: int | str, vk_message_id: int | str) -> None:
		# Сохраняем ID сообщения в ДБ:
		DB = getDefaultCollection()
		DB.update_one({"_id": self.user.TGUser.id}, {
			"$set": {
				f"Services.VK.ServiceToTelegramMIDs.{vk_message_id}": str(telegram_message_id)
			}
		})

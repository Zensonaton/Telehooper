# coding: utf-8

# В этом файле находится middle-псевдо-API, благодаря которому различные 'коннекторы' могут соединяться с основым Telegram ботом.


from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import Optional

import aiogram
import vkbottle
import vkbottle_types
import vkbottle_types.responses.account
import vkbottle_types.responses.users
from vkbottle.user import Message

import Utils
from Consts import AccountDisconnectType, MAPIServiceType
from DB import getDefaultCollection

logger = logging.getLogger(__name__)

class MiddlewareAPI:
	"""
	Middleware API, необходимое для создания общего API между Service Handler'ами.
	"""

	telegramUser: aiogram.types.User

	vkAccount: VKAccount
	isVKConnected: bool

	def __init__(self, telegramUser: aiogram.types.User, vkAccount: Optional[VKAccount] = None) -> None:
		self.vkAccount = vkAccount # type: ignore
		self.isVKConnected = (vkAccount is not None)

		self.telegramUser = telegramUser

	async def connectVKAccount(self, vk_token: str, do_init_stuff: bool = True, auth_via_password: bool = False) -> VKAccount:
		"""
		Подключает аккаунт ВКонтакте к этому Middleware API.
		`do_init_stuff` указывает, будут ли выполняться все дополнительные действия по подключению аккаунту:
		 * fetch'инг информации о пользователе,
		 * подключение VKServiceHandler'а (Longpoll)
		"""

		self.vkAccount = VKAccount(vk_token, self, auth_via_password)
		if do_init_stuff:
			await self.vkAccount.initUserInfo()
			await self.vkAccount.connectVKServiceHandler()

		return self.vkAccount

	async def sendMessage(self, message: str):
		"""
		Отправляет сообщение пользователю в Telegram.
		"""

		await self.telegramUser.bot.send_message(self.telegramUser.id, message)

	async def processServiceDisconnect(self, service_type: int = MAPIServiceType.VK, disconnect_type: int = AccountDisconnectType.INITIATED_BY_USER, send_service_messages: bool = False) -> None:
		"""
		Выполняет определённые действия при отключении сервиса/аккаунта от бота.
		"""

		# Отключаем Task:
		self.vkAccount.vkUser.polling.stop = True # type: ignore

		if disconnect_type != AccountDisconnectType.SILENT:
			# Это не было "тихое" отключение аккаунта, поэтому
			# отправляем сообщения пользователю Telegram.

			is_external = (disconnect_type == AccountDisconnectType.EXTERNAL)

			await self.telegramUser.bot.send_message(
				self.telegramUser.id,
				(
					# TODO: Поменять этот текст:
					"⚠️ Аккаунт <b>«ВКонтакте»</b> был принудительно отключён от бота Telehooper; это действие было совершено <b>внешне</b>, напримёр, <b>отозвав все сессии в настройках безопасности аккаунта</b>."
					if (is_external) else
					"ℹ️ Аккаунт <b>«ВКонтакте»</b> был успешно отключён от Telehooper."
				)
			)

		if send_service_messages:
			# Мы должны отправить сообщения в самом сервисе о отключении:
			await self.vkAccount.vkAPI.messages.send(self.vkAccount.vkFullUser.id, random_id=Utils.generateVKRandomID(), message="ℹ️ Ваш аккаунт ВКонтакте был успешно отключён от бота «Telehooper».")

		# Получаем ДБ:
		DB = getDefaultCollection()

		# И удаляем запись оттуда:
		DB.update_one(
			{
				"_id": self.telegramUser.id
			},
			{"$set": {
				"Services.VK.Auth": False,
				"Services.VK.Token": None
			}},
			upsert=True
		)

class VKServiceHandler:
	"""
	ВК Handler для работы над сообщениями.
	"""

	pollingTask: asyncio.Task

	def __init__(self, middlewareAPI: MiddlewareAPI) -> None:
		self.middlewareAPI = middlewareAPI

		self.middlewareAPI.vkAccount.vkUser.on.message()(self.onMessage)

	def runPolling(self):
		"""
		Запуск поллинга.
		"""

		@self.middlewareAPI.vkAccount.vkUser.error_handler.register_error_handler(vkbottle.VKAPIError[5])
		async def errorHandler(e: vkbottle.VKAPIError):
			# Если этот код вызывается, то значит, что пользователь отозвал разрешения ВК, и сессия была отозвана.

			# Отправляем различные сообщения о отключённом боте:
			await self.middlewareAPI.processServiceDisconnect(MAPIServiceType.VK, AccountDisconnectType.EXTERNAL)

		# Создаём Polling-задачу:
		self.pollingTask = asyncio.create_task(self.middlewareAPI.vkAccount.vkUser.run_polling(), name=f"VK Polling, id{self.middlewareAPI.vkAccount.vkFullUser.id}")

	async def serviceCommandHandler(self, msg: Message):
		"""
		Обработчик команд, отправленных внутри сервиса, т.е., например, в чате "Избранное" в ВК.
		"""

		async def _commandRecieved(msg: Message):
			await self.middlewareAPI.vkAccount.vkAPI.messages.edit(self.middlewareAPI.vkAccount.vkFullUser.id, "✅ " + msg.text, message_id=msg.id)

		if msg.text.startswith("logoff"):
			# Выходим из аккаунта:
			await _commandRecieved(msg)
			
			await self.middlewareAPI.processServiceDisconnect(MAPIServiceType.VK, AccountDisconnectType.EXTERNAL, False)

			# Отправляем сообщения:
			await self.middlewareAPI.vkAccount.vkAPI.messages.send(self.middlewareAPI.vkAccount.vkFullUser.id, random_id=Utils.generateVKRandomID(), message="ℹ️ Ваш аккаунт ВКонтакте был успешно отключён от бота «Telehooper».", reply_to=msg.id)
		elif msg.text.startswith("test"):
			await _commandRecieved(msg)

			await self.middlewareAPI.vkAccount.vkAPI.messages.send(self.middlewareAPI.vkAccount.vkFullUser.id, random_id=Utils.generateVKRandomID(), message="✅ Telegram-бот «Telehooper» работает!", reply_to=msg.id)
		elif msg.text.startswith("ping"):
			await _commandRecieved(msg)

			await self.middlewareAPI.sendMessage("[<b>ВКонтакте</b>] » pong! 👋")



	async def onMessage(self, msg: Message):
		"""
		Обработчик входящих/исходящих сообщений.
		"""

		if msg.peer_id == self.middlewareAPI.vkAccount.vkFullUser.id:
			# Мы получили сообщение в "Избранном", обрабатываем сообщение как команду,
			# но боту в ТГ ничего не даём.
			await self.serviceCommandHandler(msg)

			return

		if msg.out:
			# Мы получили сообщение, отправленное самим пользователем, игнорируем.

			return

		if abs(msg.peer_id) == int(os.environ.get("VKBOT_NOTIFIER_ID", 0)):
			# Мы получили сообщение от группы Telehooper, игнорируем.

			return

		await self.middlewareAPI.sendMessage(msg.text)

class VKAccount:
	"""
	Класс, отображающий аккаунт ВКонтакте пользователя.
	"""

	vkToken: str
	authViaPassword: bool

	vkAPI: vkbottle.API
	vkFullUser: vkbottle_types.responses.users.UsersUserFull
	vkUser: vkbottle.User
	vkAccountInfo: vkbottle_types.responses.account.AccountUserSettings

	def __init__(self, vkToken: str, middlewareAPI: MiddlewareAPI, auth_via_password: bool = False):
		self.vkToken = vkToken
		self.middlewareAPI = middlewareAPI
		self.authViaPassword = auth_via_password

		self.vkAPI = vkbottle.API(self.vkToken)
		self.vkUser = vkbottle.User(self.vkToken)


	async def initUserInfo(self):
		"""
		Обращается к API ВКонтакте, чтобы получить информацию о пользователе.
		"""

		# Получаем информацию о аккаунте пользователя, который прошёл авторизацию. Из информации используется ID пользователя.
		self.vkAccountInfo = await self.vkAPI.account.get_profile_info()

		# Получаем всю открытую информацию о пользователе.
		self.vkFullUser = (await self.vkAPI.users.get(user_ids=[self.vkAccountInfo.id]))[0]

	async def connectVKServiceHandler(self) -> VKServiceHandler:
		"""
		Создаёт VK Service Handler.
		"""

		svc = VKServiceHandler(self.middlewareAPI)
		svc.runPolling()

		return svc

	async def postAuthInit(self):
		"""Действия, выполняемые после успешной авторизации пользоваля ВКонтакте: Отправляет предупредительные сообщения, и так далее."""

		await self.initUserInfo()

		space = "&#12288;" # Символ пробела, который не удаляется при отправке сообщения ВКонтакте.
		userInfoData = f"{space}* Имя: {self.middlewareAPI.telegramUser.first_name}"

		if self.middlewareAPI.telegramUser.last_name:
			userInfoData += " {self.telegramUser.last_name}"
		userInfoData += ".\n"

		if self.middlewareAPI.telegramUser.username:
			userInfoData += f"{space}* Никнейм в Telegram: {self.middlewareAPI.telegramUser.username}.\n"
			userInfoData += f"{space}* Ссылка: https://t.me/{self.middlewareAPI.telegramUser.username}​.\n"

		userInfoData += f"{space}* Авторизация была произведена через " + ("пароль" if self.authViaPassword else f"VK ID") + ".\n"


		await self.vkAPI.messages.send(self.vkAccountInfo.id, random_id=Utils.generateVKRandomID(), message=f"""⚠️ ВАЖНАЯ ИНФОРМАЦИЯ ⚠️ {space * 15}

Привет! 🙋
Если ты видишь это сообщение, то в таком случае значит, что Telegram-бот под названием «Telehooper» был успешно подключён к твоей странице ВКонтакте. Пользователь, который подключился к вашей странице ВКонтакте сумеет делать следующее:
{space}* Читать все получаемые и отправляемые сообщения.
{space}* Отправлять сообщения.
{space}* Смотреть список диалогов.
{space}* Просматривать список твоих друзей, отправлять им сообщения.
Если подключал бота не ты, то срочно {"в настройках подключённых приложений (https://vk.com/settings?act=apps) отключи приложение «VK Messenger», либо же " if self.authViaPassword else "настройках «безопасности» (https://vk.com/settings?act=security) нажми на кнопку «Отключить все сеансы», либо же "}в этот же диалог пропиши команду «logoff», (без кавычек) и если же тут появится сообщение о успешном отключении, то значит, что бот был отключён. После отключения срочно меняй пароль от ВКонтакте, поскольку произошедшее значит, что кто-то сумел войти в твой аккаунт ВКонтакте, либо же ты забыл выйти с чужого компьютера!
Информация о пользователе, который подключил бота, будет отправлена в чат бота:
{userInfoData}
Если же это был ты, то волноваться незачем, и ты можешь просто проигнорировать всю предыдущую часть сообщения.

ℹ️ В этом диалоге можно делать следующее для управления Telehooper'ом; все команды прописываются без «кавычек»:
{space}* Проверить, подключён ли Telehooper: «test».
{space}* Отправить тестовое сообщение в Telegram: «ping».
{space}* Отключить аккаунт ВКонтакте от Telehooper: «logoff».""")

		# Пытаемся отправить оповестительное сообщение в ВК-группу:
		try:
			notifier_group_id = abs(int(os.environ["VKBOT_NOTIFIER_ID"]))

			if notifier_group_id > 0:
				await self.vkAPI.messages.send(-notifier_group_id, Utils.generateVKRandomID(), message="(это автоматическое сообщение, не обращай на него внимание.)\n\ntelehooperSuccessAuth")
		except:
			logger.warning(f"Не удалось отправить опциональное сообщение об успешной авторизации бота в ВК. Пожалуйста, проверьте настройку \"VKBOT_NOTIFIER_ID\" в .env файле. (текущее значение: {os.environ.get('VKBOT_NOTIFIER_ID')})")

		DB = getDefaultCollection()

		# Сохраняем информацию о авторизации:
		DB.update_one(
			{
				"_id": self.middlewareAPI.telegramUser.id
			},
			{"$set": {
				"_id": self.middlewareAPI.telegramUser.id,
				"TelegramUserID": self.middlewareAPI.telegramUser.id,
				"VKUserID": self.vkAccountInfo.id,
				"Services": {
					"VK": {
						"Auth": True,
						"IsAuthViaPassword": self.authViaPassword,
						"AuthDate": datetime.datetime.now(),
						"Token": self.vkToken,
					}
				}
			}},
			upsert=True
		)

	async def checkAvailability(self, no_error: bool = False) -> bool:
		"""
		Делает тестовый API-запрос к VK для проверки доступности пользователя.
		Слегка быстрее чем `initUserInfo()`, поскольку этот метод делает лишь один запрос.
		"""

		try:
			self.vkAccountInfo = await self.vkAPI.account.get_profile_info()
		except Exception as error:
			if not no_error:
				raise(error)

			return False
		else:
			return True

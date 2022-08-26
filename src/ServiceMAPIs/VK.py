# coding: utf-8

from __future__ import annotations
import asyncio

import datetime
import os
from asyncio import Task
from typing import TYPE_CHECKING

import Utils
import vkbottle
from Consts import AccountDisconnectType
from DB import getDefaultCollection
from loguru import logger
from vkbottle.tools.dev.mini_types.base.message import BaseMessageMin

from .Base import baseTelehooperAPI

if TYPE_CHECKING:
	from TelegramBot import Telehooper, TelehooperUser

class VKTelehooperAPI(baseTelehooperAPI):
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
		user.APIstorage.vk.fullUserInfo = fullUserInfo
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

	async def onNewMessage(self, user: "TelehooperUser", msg: BaseMessageMin):
		await super().onNewMessage(user)

		print("new message", msg.text)

	async def runPolling(self, user: "TelehooperUser") -> Task:
		"""
		Запускает Polling для получения сообщений.
		"""

		if user.APIstorage.vk.pollingTask:
			# Polling уже запущен, не делаем ничего.

			logger.warning(f"Была выполнена попытка повторного запуска polling'а у пользователя с TID {user.TGUser.id}")

			return user.APIstorage.vk.pollingTask

		@user.vkUser.on.message()
		async def _onMessage(msg: BaseMessageMin):
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

		# Отключаем Task, используя следующий метод:
		# task.cancel() использовать нельзя из-за бага библиотеки vkbottle.
		#
		# https://github.com/vkbottle/vkbottle/issues/504
		# user.vkUser.polling.stop = True # type: ignore (переменной нет в vkbottle_types)

		user.APIstorage.vk.pollingTask.cancel() # type: ignore

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

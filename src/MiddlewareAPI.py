# coding: utf-8

# В этом файле находится middle-псевдо-API, благодаря которому различные 'коннекторы' могут соединяться с основым Telegram ботом.

import logging
import os
import aiogram

import vkbottle
import vkbottle_types.responses.account
import vkbottle_types.responses.users
from aiogram.types import User
# from ServiceHandlers.VK import VKServiceHandler
import Utils

logger = logging.getLogger(__name__)

class VKAccount:
	"""
	Класс, отображающий аккаунт ВКонтакте пользователя.
	"""

	vkToken: str
	telegramUser: User
	authViaPassword: bool

	vkAPI: vkbottle.API
	vkFullUser: vkbottle_types.responses.users.UsersUserFull
	vkUser: vkbottle.User
	vkAccountInfo: vkbottle_types.responses.account.AccountUserSettings


	def __init__(self, vkToken: str, telegramUser: User, auth_via_password: bool = False):
		self.vkToken = vkToken
		self.telegramUser = telegramUser
		self.authViaPassword = auth_via_password

		self.vkAPI = vkbottle.API(self.vkToken)
		self.vkUser = vkbottle.User(self.vkToken)

		from ServiceHandlers.VK import VKServiceHandler
		VKServiceHandler(MiddlewareAPI(self.vkUser, self.telegramUser))




	async def initUserInfo(self):
		# Получаем информацию о аккаунте пользователя, который прошёл авторизацию. Из информации используется ID пользователя.
		self.vkAccountInfo = await self.vkAPI.account.get_profile_info()

		# Получаем всю открытую информацию о пользователе.
		self.vkFullUser = (await self.vkAPI.users.get(user_ids=[self.vkAccountInfo.id]))[0]

	async def postAuthInit(self):
		"""Действия, выполняемые после успешной авторизации пользоваля ВКонтакте: Отправляет предупредительные сообщения, и так далее."""

		await self.initUserInfo()

		space = "&#12288;" # Символ пробела, который не удаляется при отправке сообщения ВКонтакте.
		userInfoData = f"{space}* Имя: {self.telegramUser.first_name}"

		if self.telegramUser.last_name:
			userInfoData += " {self.telegramUser.last_name}"
		userInfoData += ".\n"

		if self.telegramUser.username:
			userInfoData += f"{space}* Никнейм в Telegram: {self.telegramUser.username}.\n"
			userInfoData += f"{space}* Ссылка: https://t.me/{self.telegramUser.username}​.\n"
	
		userInfoData += f"{space}* Авторизация была произведена через " + ("пароль от ВКонтакте" if self.authViaPassword else f"VK ID") + ".\n"


		await self.vkAPI.messages.send(self.vkAccountInfo.id, random_id=Utils.generateVKRandomID(), message=f"""⚠️ ВАЖНАЯ ИНФОРМАЦИЯ ⚠️ {space * 15}

Привет! 🙋
Если ты видишь это сообщение, то в таком случае значит, что Telegram-бот под названием «Telehooper» был успешно подключён к твоей странице ВКонтакте. Пользователь, который подключился к вашей странице ВКонтакте сумеет делать следующее:
{space}* Читать все получаемые и отправляемые сообщения.
{space}* Отправлять сообщения.
{space}* Смотреть список диалогов.
{space}* Просматривать список твоих друзей, отправлять им сообщения.
Если подключал бота не ты, то {"срочно в настройках подключённых приложений (https://vk.com/settings?act=apps) отключи приложение «VK Messenger», либо же " if self.authViaPassword else ""}в этот же диалог пропиши команду «logoff», (без кавычек) и если же тут появится сообщение о успешном отключении, то значит, что бот был отключён. После отключения срочно меняй пароль от ВКонтакте, поскольку произошедшее значит, что кто-то сумел войти в твой аккаунт ВКонтакте, либо же ты забыл выйти с чужого компьютера!
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
			logger.warning(f"Не удалось отправить опциональное сообщение об успешной авторизации бота в ВК. Пожалуйста, проверьте настройку \"VKBOT_NOTIFIER_ID\" в .env файле. (текущее значение: {os.environ['VKBOT_NOTIFIER_ID']})")

class MiddlewareAPI:
	"""
	Middleware API, необходимое для создания общего API между Service Handler'ами.
	"""

	vkUser: vkbottle.User
	telegramUser: aiogram.types.User

	def __init__(self, vkUser: vkbottle.User, telegramUser: aiogram.types.User) -> None:
		self.vkUser = vkUser
		self.telegramUser = telegramUser

	async def sendMessage(self, message: str):
		"""
		Отправляет сообщение пользователю в Telegram.
		"""

		await self.telegramUser.bot.send_message(self.telegramUser.id, message)


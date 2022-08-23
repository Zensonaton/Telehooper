# coding: utf-8

from __future__ import annotations

from typing import TYPE_CHECKING
import vkbottle

from .Base import baseTelehooperAPI

if TYPE_CHECKING:
	from TelegramBot import Telehooper, TelehooperUser

class VKTelehooperAPI(baseTelehooperAPI):
	"""
	API для работы над ВКонтакте.
	"""

	def __init__(self, telehooper_bot: "Telehooper") -> None:
		super().__init__(telehooper_bot)

		available = True
		serviceCodename = "vk"
		serviceName = "ВКонтакте"

	async def connect(self, user: "TelehooperUser", token: str):
		await super().connect(user)

		# Пытаемся подключиться к странице ВК.

		try:
			print("connection")
			vkAccount = vkbottle.API(token)
		except:
			print("ОШБЫКА")

		return


		space = "&#12288;" # Символ пробела, который не удаляется при отправке сообщения ВКонтакте.
		userInfoData = f"{space}• Имя: {user.TGUser.first_name}"

		if user.TGUser.last_name:
			userInfoData += " {self.telegramUser.last_name}"
		userInfoData += ".\n"

		if user.TGUser.username:
			userInfoData += f"{space}• Никнейм в Telegram: {user.TGUser.username}.\n"
			userInfoData += f"{space}• Ссылка: https://t.me/{user.TGUser.username}​.\n"

		userInfoData += f"{space}• Авторизация была произведена через " + ("пароль" if False else f"VK ID") + ".\n"


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
				"_id": user.TGUser.id
			},
			{"$set": {
				"_id": user.TGUser.id,
				"TelegramUserID": user.TGUser.id,
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
		res = DB.find_one({"_id": user.TGUser.id})
		if res:
			vkService = res["Services"]["VK"]
			if not vkService.get("DownloadImage"):
				vkService["DownloadImage"] = await vkbottle.PhotoMessageUploader(self.vkAPI).upload("downloadImage.png")
				DB.update_one({"_id": user.TGUser.id}, {"$set": {"Services.VK.DownloadImage": vkService["DownloadImage"]}})

			return vkService["DownloadImage"]

		return None

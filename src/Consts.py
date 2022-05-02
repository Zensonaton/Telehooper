# coding: utf-8

REQUIREDENVVARS = {
	"TOKEN": "Токен Telegram-бота. Его можно получить у @BotFather.",
	"MONGODB_HOST": "Хост для подключения к MongoDB. По умолчанию localhost.",
	"MONGODB_PORT": "Порт для подключения к MongoDB. По умолчанию 27017.",
	"MONGODB_DBNAME": "Название базы данных MongoDB.",
	"MONGODB_COLLECTION": "Название коллекции в базе данных MongoDB.",
	"VKBOT_NOTIFIER_ID": "ID VK группы, в которую будет отправляться сообщение для уведомление о подключении нового пользователя. Отрицательное, числовое значение. По умолчанию 213024897. Используй число 0 для отключения.",
}

class officialVKAppCreds:
	"""
	Класс/Enum для хранения официальных данных приложений ВК. Необходимо для авторизации через логин-пароль.
	"""

	# Взято из:
	# https://github.com/negezor/vk-io/blob/master/packages/authorization/src/constants.ts#L63-L88

	class appCredential:
		"""
		Класс с информацией о приложении ВК.
		"""

		clientID: int
		clientSecret: str

		def __init__(self, clientID: int, clientSecret: str) -> None:
			self.clientID = clientID
			self.clientSecret = clientSecret

	ANDROID = appCredential(2274003, "hHbZxrka2uZ6jB1inYsH")
	WINDOWS = appCredential(3697615, "AlVXZFMUqyrnABp8ncuU")
	WINDOWS_PHONE = appCredential(3502557, "PEObAuQi6KloPM4T30DV")
	IPHONE = appCredential(3140623, "VeWdmVclDCtn6ihuP1nt")
	IPAD = appCredential(3682744, "mY6CDUswIVdJLCD3j15n")
	VK_ME = appCredential(6146827, "qVxWRF1CwHERuIrKBnqe")

class vkscopes:
	"""
	Класс/Enum для хранения информации о scope/разрешениях для приложения.
	"""

	class vkscope:
		scopeName: str
		scopeID: int

		def __init__(self, scopeName: str, scopeID: int) -> None:
			self.scopeName = scopeName
			self.scopeID = scopeID

	NOTIFY = vkscope("notify", 1)
	FRIENDS = vkscope("friends", 2)
	PHOTOS = vkscope("photos", 4)
	AUDIO = vkscope("audio", 8)
	VIDEO = vkscope("video", 16)
	PAGES = vkscope("pages", 128)
	LINK = vkscope("link", 256)
	STATUS = vkscope("status", 1024)
	NOTES = vkscope("notes", 2048)
	MESSAGES = vkscope("messages", 4096)
	WALL = vkscope("wall", 8192)
	ADS = vkscope("ads", 32768)
	OFFLINE = vkscope("offline", 65536)
	DOCS = vkscope("docs", 131072)
	GROUPS = vkscope("groups", 262144)
	NOTIFICATIONS = vkscope("notifications", 524288)
	STATS = vkscope("stats", 1048576)
	EMAIL = vkscope("email", 4194304)
	MARKET = vkscope("market", 134217728)

class InlineButtonCallbacks:
	ADD_VK_ACCOUNT = "add_vk"
	VK_LOGIN_VIA_PASSWORD = "add_vk_password"
	VK_LOGIN_VIA_VKID = "add_vk_vkid"
	BACK_TO_SERVICE_SELECTOR = "back_to_service_selector"

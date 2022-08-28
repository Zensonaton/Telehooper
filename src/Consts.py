# coding: utf-8

REQUIREDENVVARS = {
	"TOKEN": "Токен Telegram-бота. Его можно получить у @BotFather.",
	"MONGODB_HOST": "Хост для подключения к MongoDB. По умолчанию localhost.",
	"MONGODB_PORT": "Порт для подключения к MongoDB. По умолчанию 27017.",
	"MONGODB_USER": "Пользователь для подключения к MongoDB. Может быть пустым. https://www.mongodb.com/docs/manual/reference/method/db.createUser/",
	"MONGODB_PWD": "Пароль пользователя для подключения к MongoDB. Может быть пустым. https://www.mongodb.com/docs/manual/reference/method/db.createUser/",
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

class InlineButtonCallbacks:
	class CommandCallers:
		ME = "command_self"
		THIS = "command_this"
		CONVERT = "command_convert_to_dialogue"

	class CommandActions:
		CONVERT_TO_DIALOGUE = "action_convert_to_dialogue"
		DISCONNECT_SERVICE = "action_disconnect_service"
		DIALOGUE_SELECT_VK = "action_dialogue-vk:"
		CONVERT_TO_REGULAR_GROUP = "action_convert_to_group"

	class CommandMenus:
		VK_LOGIN_VKID = "menu_login_vkid"
		VK_LOGIN_PASSWORD = "menu_login_pass"

	class CancelAction:
		CANCEL_DELETE_MESSAGE = "cancel_delete_message"
		CANCEL_EDIT_MESSAGE = "cancel_edit_message"
		CANCEL_HIDE_BUTTONS = "cancel_hide_buttons"

	DO_NOTHING = "do_nothing"

class AccountDisconnectType:
	INITIATED_BY_USER = 1
	EXTERNAL = 2
	SILENT = 3
	ERRORED = 4

class MAPIServiceType:
	VK = 1

class CommandThrottleNames:
	VK_LOGIN = "vklogin"
	VK_LOGIN_VKID = "vkloginviavkid"
	DIALOGUE_CONVERT = "grouptodialogueconvert"
	SERVICES_LIST = "services"
	THIS_DIALOGUE = "this"

VK_OAUTH_URL = "https://oauth.vk.com/authorize?client_id=2685278&scope=69634&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1"

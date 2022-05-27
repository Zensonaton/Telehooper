# coding: utf-8

REQUIREDENVVARS = {
	"TOKEN": "Токен Telegram-бота. Его можно получить у @BotFather.",
	"MONGODB_HOST": "Хост для подключения к MongoDB. По умолчанию localhost.",
	"MONGODB_PORT": "Порт для подключения к MongoDB. По умолчанию 27017.",
	"MONGODB_DBNAME": "Название базы данных MongoDB.",
	"MONGODB_COLLECTION": "Название коллекции в базе данных MongoDB.",
	"VKBOT_NOTIFIER_ID": "ID VK группы, в которую будет отправляться сообщение для уведомление о подключении нового пользователя. Отрицательное, числовое значение. По умолчанию 213024897. Используй число 0 для отключения.",
}

class InlineButtonCallbacks:
	ADD_VK_ACCOUNT = "add_vk"
	VK_LOGIN_VIA_PASSWORD = "add_vk_password"
	VK_LOGIN_VIA_VKID = "add_vk_vkid"
	BACK_TO_SERVICE_SELECTOR = "back_to_service_selector"
	DISCONNECT_SERVICE = "disconnect"
	CANCEL_GROUP_TRANSFORM = "cancel_to_servicegroup_transform"
	CONVERT_GROUP_TO_DIALOGUE = "convert_to_dialogue"
	CANCEL_DELETE_CUR_MESSAGE = "cancel"
	CANCEL_EDIT_CUR_MESSAGE = "cancel_edit"
	BACK_TO_GROUP_CONVERTER = "back_group_converter"
	DIALOGUE_SELECTOR_MENU_VK = "dialogue_select-vk"
	DIALOGUE_SELECT_VK = "dialogue-vk:"
	THIS_COMMAND = "this_command"

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

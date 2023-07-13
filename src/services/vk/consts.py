# coding: utf-8

from consts import COMMANDS_USERS_GROUPS_CONVERTED


VK_OAUTH_URL = "https://oauth.vk.com/authorize?client_id=2685278&scope=69634&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1"

VK_USERS_GET_AUTOUPDATE_SECS = 12 * 60 * 60
VK_USER_INACTIVE_SECS = 7 * 24 * 60 * 60

VK_INVISIBLE_CHARACTER = "&#12288;"

VK_GROUP_DIALOGUE_COMMANDS = {
	**COMMANDS_USERS_GROUPS_CONVERTED,

	"delete": "[ВК] Удаление выбранного сообщения для всех",
    "read": "[ВК] Прочтение последних сообщений"
}

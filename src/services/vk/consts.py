# coding: utf-8

from consts import COMMANDS_USERS_GROUPS_CONVERTED


VK_OAUTH_URL = "https://oauth.vk.com/authorize?client_id=2685278&scope=200706&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1"
"""OAuth-ссылка для получения токена ВКонтакте."""
VK_USERS_GET_AUTOUPDATE_SECS = 12 * 60 * 60 # 12 часов.
"""Время в секундах, отображающее интервал для автообновления информации о пользователях."""
VK_USER_INACTIVE_SECS = 7 * 24 * 60 * 60 # 7 дней.
"""Время в секундах, отображающее интервал для определения неактивности пользователя. После этого времени пользователь считается неактивным, и информация о нём перестанет обновляться."""
VK_USER_REMOVAL_SECS = 30 * 24 * 60 * 60 # 30 дней.
"""Время в секундах, отображающее интервал для определения удаления кэшированной информации пользователя."""
VK_INVISIBLE_CHARACTER = "&#12288;"
"""Невидимый символ, используемый для отображения пустых строк в сообщениях."""
VK_GROUP_DIALOGUE_COMMANDS = {
	**COMMANDS_USERS_GROUPS_CONVERTED,

	"delete": "[ВК] Удаление выбранного сообщения для всех",
    "read": "[ВК] Прочтение последних сообщений"
}
"""Словарь, содержащий команды, которые могут быть использованы в беседах с группами."""
VK_MESSAGES_API_RESTRICTION_DOCS_VK_URL = "https://dev.vk.com/reference/roadmap#Ограничение Messages API"
"""Ссылка на документацию ВКонтакте, описывающую ограничения Messages API."""
VK_MESSAGES_API_RESTRICTION_DOCS_GITHUB_URL = "https://github.com/Zensonaton/Telehooper/blob/rewrite/src/services/vk/README.md#ограничения-messaging-api"

# coding: utf-8

from consts import COMMANDS_USERS_GROUPS_CONVERTED, GITHUB_SOURCES_URL


VK_OAUTH_URL = "https://oauth.vk.com/authorize?client_id=2685278&scope=69634&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1"
"""OAuth-ссылка для получения токена ВКонтакте."""
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
VK_MESSAGES_API_RESTRICTION_DOCS_GITHUB_URL = f"{GITHUB_SOURCES_URL}/blob/rewrite/src/services/vk/README.md#ограничения-messaging-api"
"""Ссылка на Github-документацию об ограничении VK Messaging API."""
VK_LONGPOLL_GLOBAL_ERRORS_AMOUNT = 5
"""Максимальное количество глобальных ошибок VK Longpoll, при достижении которых автоматически отключается longpoll."""

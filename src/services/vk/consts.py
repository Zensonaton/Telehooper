# coding: utf-8

VK_OAUTH_URL = "https://oauth.vk.com/authorize?client_id=2685278&scope=69634&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1"
VK_USERS_GET_AUTOUPDATE_SECS = 12 * 60 * 60
VK_USER_INACTIVE_SECS = 7 * 24 * 60 * 60

class VKAppCredentials:
	"""
	Оффициальные данные для авторизации от приложений VK. Необходимо для авторизации через логин-пароль.

	Источник: https://github.com/negezor/vk-io/blob/master/packages/authorization/src/constants.ts#L63C16-L91
	"""

	class VKAppCredential:
		"""
		Класс с информацией о приложении ВК.
		"""

		clientID: int
		clientSecret: str

		def __init__(self, clientID: int, clientSecret: str) -> None:
			self.clientID = clientID
			self.clientSecret = clientSecret

	ANDROID = VKAppCredential(2274003, "hHbZxrka2uZ6jB1inYsH")
	WINDOWS = VKAppCredential(3697615, "AlVXZFMUqyrnABp8ncuU")
	WINDOWS_PHONE = VKAppCredential(3502557, "PEObAuQi6KloPM4T30DV")
	IPHONE = VKAppCredential(3140623, "VeWdmVclDCtn6ihuP1nt")
	IPAD = VKAppCredential(3682744, "mY6CDUswIVdJLCD3j15n")
	VK_ME = VKAppCredential(6146827, "qVxWRF1CwHERuIrKBnqe")

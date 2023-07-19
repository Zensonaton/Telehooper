# coding: utf-8

import random
import re


def extract_access_token_from_url(url: str) -> str:
	"""
	Извлекает ACCESS_TOKEN из URL. Используется для ВКонтакте-авторизации.
	"""

	regex_result = re.search(r"access_token=([^&]+)", url)
	if regex_result:
		return regex_result.group(1)

	raise Exception("Не удалось извлечь ACCESS_TOKEN из URL.")

def extract_user_id_from_url(url: str) -> int:
	"""
	Извлекает USER_ID из URL. Используется для ВКонтакте-авторизации.
	"""

	regex_result = re.search(r"user_id=([^&]+)", url)
	if regex_result:
		return int(regex_result.group(1))

	raise Exception("Не удалось извлечь USER_ID из URL.")

def random_id() -> int:
	"""
	Создаёт случайный ID для отправки сообщений во ВКонтакте.
	"""

	return random.randint(-2147483647, 2147483648)

def get_message_flags(flags: int) -> tuple[bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool]:
	"""
	Выдаёт tuple с флагами сообщения. [Документация ВК](https://vk.com/dev/using_longpoll_3).

	Значения в tuple:
	`(UNREAD, OUTBOX, REPLIED, REPLIED, CHAT, FRIENDS, SPAM, DELЕTЕD, FIXED, MEDIA, HIDDEN, DELETE_FOR_ALL, NOT_DELIVERED)`
	"""

	def _value(flag: int) -> bool:
		"""
		Если текущее значение `flags` больше чем `flag`, то возвращает `True`, и отнимает от `flags` значение `flag`.
		"""

		nonlocal flags

		if flags >= flag:
			flags -= flag

			return True

		return False

	NOT_DELIVERED 	= _value(2 ** 18) 	# 12
	DELETE_FOR_ALL 	= _value(2 ** 17) 	# 11
	HIDDEN 			= _value(2 ** 16) 	# 10
	MEDIA 			= _value(2 ** 9) 	# 9
	FIXED 			= _value(2 ** 8) 	# 8
	DELETED 		= _value(2 ** 7) 	# 7
	SPAM 			= _value(2 ** 6) 	# 6
	FRIENDS 		= _value(2 ** 5) 	# 5
	CHAT 			= _value(2 ** 4) 	# 4
	IMPORTANT 		= _value(2 ** 3) 	# 3
	REPLIED 		= _value(2 ** 2) 	# 2
	OUTBOX 			= _value(2 ** 1) 	# 1
	UNREAD 			= _value(2 ** 0) 	# 0

	return (UNREAD, OUTBOX, REPLIED, IMPORTANT, CHAT, FRIENDS, SPAM, DELETED, FIXED, MEDIA, HIDDEN, DELETE_FOR_ALL, NOT_DELIVERED)

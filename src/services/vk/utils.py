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

class VKLongpollMessageFlags:
	"""
	Класс, который парсит флаги сообщения ВКонтакте.

	Дополнительная информация: https://dev.vk.com/api/user-long-poll/getting-started#Флаги сообщений
	"""

	not_delivered: bool
	"""Сообщение не было доставлено. Deprecated."""
	delete_for_all: bool
	"""Сообщение было удалено для всех пользователей."""
	hidden: bool
	"""Сообщение является ненастоящим, невидимым. Такие сообщения появляются при открытии диалога с сообществом."""
	media: bool
	"""Сообщение содержит медиа-вложения. Deprecated."""
	fixed: bool
	"""Сообщение было проверено пользователем на спам. Deprecated."""
	deleted: bool
	"""Сообщение удалено."""
	spam: bool
	"""Сообщение помечено как спам."""
	friends: bool
	"""Сообщение отправлено другом. Не применяется для сообщений из групповых бесед."""
	chat: bool
	"""Сообщение отправлено через чат. Deprecated."""
	important: bool
	"Помеченное сообщение как важное."
	replied: bool
	"""На сообщение был создан ответ."""
	outbox: bool
	"""Указывает, что сообщение является исходящим."""
	unread: bool
	"""Указывает, что сообщение является непрочитанным."""

	_input_flags: int
	"""Сырое значение флагов сообщения."""

	def __init__(self, flags: int) -> None:
		self._input_flags = flags

		def _get_flag(flag_upper_value: int) -> bool:
			"""
			Проверяет, установлен ли флаг `flag`.
			"""

			nonlocal flags

			if flags >= flag_upper_value:
				flags -= flag_upper_value

				return True

			return False

		self.hidden = _get_flag(2 ** 16)
		self.media = _get_flag(2 ** 9)
		self.fixed = _get_flag(2 ** 8)
		self.deleted = _get_flag(2 ** 7)
		self.spam = _get_flag(2 ** 6)
		self.delete_for_all = self.spam
		self.not_delivered = self.spam
		self.friends = _get_flag(2 ** 5)
		self.chat = _get_flag(2 ** 4)
		self.important = _get_flag(2 ** 3)
		self.replied = _get_flag(2 ** 2)
		self.outbox = _get_flag(2 ** 1)
		self.unread = _get_flag(2 ** 0)

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

# coding: utf-8

import asyncio
import io
import random
import re

from PIL import Image

import utils


def extract_access_token_from_url(url: str) -> str:
	"""
	Извлекает ACCESS_TOKEN из URL. Используется для ВКонтакте-авторизации.
	"""

	regex_result = re.search(r"access_token=([^&]+)", url)
	if regex_result:
		return regex_result.group(1)

	raise Exception("Не удалось извлечь ACCESS_TOKEN из URL.")

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
	_flags_dict: dict[str, bool]
	"""Словарь с флагами сообщения, их названиями и значениями."""

	def __init__(self, flags: int) -> None:
		self._input_flags = flags

		self.unread = (flags & 1) != 0
		self.outbox = (flags & 2) != 0
		self.replied = (flags & 4) != 0
		self.important = (flags & 8) != 0
		self.chat = (flags & 16) != 0
		self.friends = (flags & 32) != 0
		self.spam = (flags & 64) != 0
		self.deleted = (flags & 128) != 0
		self.fixed = (flags & 256) != 0
		self.media = (flags & 512) != 0
		self.hidden = (flags & 65536) != 0
		self.delete_for_all = (flags & (1 << 6)) != 0
		self.not_delivered = (flags & (1 << 6)) != 0

		self._flags_dict = {
			"unread": self.unread,
			"outbox": self.outbox,
			"replied": self.replied,
			"important": self.important,
			"chat": self.chat,
			"friends": self.friends,
			"spam": self.spam,
			"deleted": self.deleted,
			"fixed": self.fixed,
			"media": self.media,
			"hidden": self.hidden,
			"delete_for_all": self.delete_for_all,
			"not_delivered": self.not_delivered
		}

	def __str__(self) -> str:
		return f"VKLongpollMessageFlags({', '.join([flag for flag, value in self._flags_dict.items() if value])})"

def create_message_link(peer_id: int | str | None, message_id: int | str, use_mobile: bool = False) -> str:
	"""
	Возвращает ссылку на сообщение из ВКонтакте. При переходе по ней, пользователь автоматически перейдёт в диалог, где было выбрано это сообщение.

	:param peer_id: ID диалога. Если `use_mobile` равен `True`, то это поле можно пропустить.
	:param message_id: ID сообщения.
	:param use_mobile: Использовать ли мобильную версию сайта (`m.vk.com`).
	"""

	if not use_mobile and peer_id is None:
		raise Exception("Не указан ID диалога")

	return f"https://m.vk.com/mail?act=msg&id={message_id}" if use_mobile else f"https://vk.com/im?sel={peer_id}&msgid={message_id}"

def create_dialogue_link(peer_id: int, use_mobile: bool = False) -> str:
	"""
	Возвращает ссылку на диалог ВКонтакте.

	:param peer_id: ID диалога.
	:param use_mobile: Использовать ли мобильную версию сайта (`m.vk.com`).
	"""

	if use_mobile and peer_id > 2e9:
		peer_id = int(peer_id - 2e9)

	return f"https://m.vk.com/mail?act=show&chat={peer_id}" if use_mobile else f"https://vk.com/im?sel={peer_id}"

async def prepare_sticker(sticker: bytes) -> bytes:
	"""
	Подготавливает стикер для отправки в ВКонтакте. Данный метод изменяет размеры стикера, дабы отправляемое графити не было слишком большим.

	:param sticker: Стикер, который нужно подготовить.
	"""

	def _inner() -> bytes:
		"""
		Внутренняя функция, которая запускается в отдельном потоке.
		"""

		img = Image.open(io.BytesIO(sticker))

		height = img.height
		width = img.width

		height_new = int(utils.clamp(height, 32, 128))
		width_new = int(width / (height / utils.clamp(height, 32, 128)))

		if height == height_new and width == width_new:
			return sticker

		img = img.resize((width_new, height_new))

		img_bytes = io.BytesIO()
		img.save(img_bytes, format="PNG")

		return img_bytes.getvalue()

	return await asyncio.to_thread(_inner)

def get_attachment_key(attachment: dict, type: str | None = None, include_access_key: bool = True) -> str:
	"""
	Извлекает из объекта attachment данные о вложении, передавая строку вида `photo123456_123456_abcdefg`.

	:param attachment: Объект вложения, из которого будет излекаться информация.
	:param type: Тип вложения, который используется в самом начале. Если не указывать, то пропускается.
	:param include_access_key: Указывает, будет ли данный метод добавлять поле access_key в итоговую строку. Иногда это поле отсутствует.
	"""

	output = ""
	if type is not None:
		output += type

	output += f"{attachment['owner_id']}_{attachment.get('id') or attachment.get('video_id')}"

	if include_access_key and "access_key" in attachment:
		output += f"_{attachment['access_key']}"

	return output

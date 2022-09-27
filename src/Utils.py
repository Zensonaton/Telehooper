# coding: utf-8

import base64
import hashlib
import io
import os
import random
import re
from typing import Any, Literal, Tuple

import aiohttp
from aiogram.types import InputFile
from cryptography.fernet import Fernet


def parseStrAsBoolean(value: str | bool) -> bool:
	"""
	Парсит строку в булевое значение.
	"""

	if isinstance(value, bool):
		return value
	elif value.lower().strip() in ["true", "1", "yes", "да"]:
		return True
	elif value.lower().strip() in ["false", "0", "no", "нет"]:
		return False
	else:
		raise Exception(f"Неверное значение переменной: \"{value}\". Ожидалось значение \"Yes\", \"No\", \"True\" или \"False\".")

def extractAccessTokenFromFullURL(url: str) -> str:
	"""
	Извлекает ACCESS_TOKEN из URL. Используется для ВКонтакте-авторизации.
	"""

	regex_result = re.search(r"access_token=([^&]+)", url)
	if regex_result:
		return regex_result.group(1)

	raise Exception("Не удалось извлечь ACCESS_TOKEN из URL.")

def extractUserIDFromFullURL(url: str) -> int:
	"""
	Извлекает USER_ID из URL. Используется для ВКонтакте-авторизации.
	"""

	regex_result = re.search(r"user_id=([^&]+)", url)
	if regex_result:
		return int(regex_result.group(1))

	raise Exception("Не удалось извлечь USER_ID из URL.")

def generateVKRandomID() -> int:
	"""
	Создаёт случайный ID для отправки сообщений во ВКонтакте.
	"""

	return random.randint(-2147483647, 2147483648)

def getFirstAvailableValueFromClass(cls, *keys: str, default = None):
	"""
	Возвращает первое доступное значение из класса.
	"""

	for key in keys:
		if hasattr(cls, key):
			return cls.__dict__.get(key)

	return default

def getFirstAvailableValueFromDict(object, *keys: str, default = None):
	"""
	Возвращает первое доступное значение из словаря.
	"""

	for key in keys:
		if key in object:
			return object.get(key)

	return default

def isURL(url: str) -> bool:
	"""
	Проверяет, является ли строка URL или нет.
	"""

	return re.match(r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$", url) is not None

def clamp(number: float, value_min: float, value_max: float) -> float:
	"""
	Ограничивает значение `number` в пределах `value_min` и `value_max`.
	"""

	return max(value_min, min(number, value_max))

def traverseDict(object: dict, *keys: str, default: Any = None):
	"""
	Достаёт значение из `object`, используя N-ное количество ключей. Если что-то пошло не так, и функция не сумела найти какое-то значение, то она просто вернёт значение `default`.

	Пример:
	```python
	someObject = {
		"hi": {
			"test": {
				"foo": {
					"bar": True
				}
			}
		}
	}

	print(
		safeGet(object, "hi", "test", "foo", "bar")
	)
	# True
	```
	"""

	value = object.copy()
	for key in keys:
		if not key:
			break

		if not isinstance(value, dict) or key not in value:
			return default

		value = value[key]

	return value

def getDictValuesByKeyPrefixes(object: dict, prefix: str):
	"""
	Возвращает `dict` объект со всеми значениями у `object`, префикс ключей которых совпадает со значением `prefix`.
	"""

	return {k: v for k, v in object.items() if str(k).startswith(prefix)}

def encryptWithEnvKey(input: str) -> str:
	"""
	Шифрует строку `input` ключём шифрования из `.env`-файла.
	"""

	# Проверяем, есть ли у нас ключ для шифрования в .env-файле:
	key = os.environ.get("TOKEN_ENCRYPT_KEY")
	if not key:
		# Ключа нет, не шифруем, возвращаем такое же значение.

		return input


	# Ключ шифрования есть, тогда шифруем:

	return Fernet(key).encrypt(input.encode()).decode()

def decryptWithEnvKey(input: str) -> str:
	"""
	Расшифровывает строку `input` ключём шифрования из `.env`-файла.
	"""

	# Проверяем, есть ли у нас ключ для шифрования в .env-файле:
	key = os.environ.get("TOKEN_ENCRYPT_KEY")
	if not key:
		# Ключа нет, не расшифровываем, возвращаем такое же значение.

		return input


	# Ключ шифрования есть, тогда расшифровываем:

	return Fernet(key).decrypt(input.encode()).decode()

def encryptWithKey(input: str, key: str) -> str:
	"""
	Шифрует строку `input` с ключём `key`.
	"""

	hlib = hashlib.md5()
	hlib.update(key.encode())

	return Fernet(
		base64.urlsafe_b64encode(hlib.hexdigest().encode())
	).encrypt(
		input.encode()
	).decode()

def decryptWithKey(input: str, key: str) -> str:
	"""
	Расшифровывает строку `input` с ключём `key`.
	"""

	hlib = hashlib.md5()
	hlib.update(key.encode())

	return Fernet(
		base64.urlsafe_b64encode(hlib.hexdigest().encode())
	).decrypt(
		input.encode()
	).decode()

def md5hash(input: str) -> str:
	"""
	Выдаёт MD5-хэш строки.
	"""

	return hashlib.md5(input.encode()).hexdigest()

def sha256hash(input: str) -> str:
	"""
	Выдаёт SHA256-хэш строки.
	"""

	return hashlib.sha256(input.encode()).hexdigest()

def getVKMessageFlags(flags: int) -> Tuple[bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool]:
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



_bytes = bytes
class File:
	"""
	Класс, являющийся файлом.
	"""

	url: str | None
	path: str | None
	aiofile: InputFile | None
	bytes: _bytes | None
	filename: str | None
	uid: str | None

	type: Literal["photo", "sticker", "voice", "video", "file"]

	ready: bool = False

	def __init__(self, path_url_bytes_file: str | InputFile | io.IOBase | _bytes, file_type: Literal["photo", "sticker", "voice", "video", "file"] = "photo", uid: str | None = None, filename: str | None = None) -> None:
		self.type = file_type
		self.uid = uid

		self.url = None
		self.path = None
		self.aiofile = None
		self.bytes = None
		self.filename = filename

		if isinstance(path_url_bytes_file, str):
			if isURL(path_url_bytes_file):
				self.url = path_url_bytes_file
			else:
				self.path = path_url_bytes_file
		elif isinstance(path_url_bytes_file, InputFile):
			self.aiofile = path_url_bytes_file
		elif isinstance(path_url_bytes_file, io.IOBase):
			self.bytes = path_url_bytes_file.read()
		else:
			self.bytes = path_url_bytes_file



	async def parse(self):
		"""
		Парсит файл: если была дана ссылка, то файл скачивается в память, если путь - загружается, ...
		"""

		if self.ready:
			return self

		if self.url:
			async with aiohttp.ClientSession() as session:
				async with session.get(self.url) as response:
					self.bytes = await response.read()
					
					if not self.filename:
						self.filename = response.headers.get("Content-Disposition", "filename=unknown").split("filename=")[-1].strip('"')[-1]
		elif self.path:
			assert os.path.exists(self.path), f"Файл {self.path} не существует в системе"

			self.bytes = open(self.path, "rb").read()
			if not self.filename:
				self.filename = os.path.basename(self.path)

		if self.bytes and not self.aiofile:
			self.aiofile = InputFile(io.BytesIO(self.bytes), filename=self.filename)


		self.ready = True
		return self

	def __str__(self) -> str:
		return "<File class>"

def seconds_to_userfriendly_string(seconds, max=2, minutes=True, hours=True, days=True, weeks=False, months=False, years=False, decades=False):
	"""Преобразовывает время, отображённое в секундах, как строку вида "5 часов, 17 секунд".

	Args:
		seconds ([type]): [description]
		max (int, optional): [description]. Defaults to 2.
		minutes (bool, optional): [description]. Defaults to True.
		hours (bool, optional): [description]. Defaults to True.
		days (bool, optional): [description]. Defaults to True.
		weeks (bool, optional): [description]. Defaults to False.
		months (bool, optional): [description]. Defaults to False.
		years (bool, optional): [description]. Defaults to False.
		decades (bool, optional): [description]. Defaults to False.

	Returns:
		[type]: [description]
	"""

	seconds = int(seconds)

	if seconds < 0: seconds = -seconds
	newSeconds = seconds; string = []; values = [60, 3600, 86400, 604800, 2678400, 31536000, 315360000]; maxCount = max; valuesgot = {"decades": 0, "years": 0, "months": 0, "weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}; stringslocal = [["век","века","века","века","веков"], ["год","года","года","года","лет"],["месяц","месяца","месяца","месяца","месяцев"],["неделя","недели","недели","неделей"],["день","дня","дня","дней"],["час","часа","часа","часов"],["минута","минуты","минуты","минут",],["секунда","секунды","секунды","секунд"]]
	while True:
		if newSeconds >= values[6] and decades: newSeconds -= values[6]; valuesgot["decades"] += 1
		elif newSeconds >= values[5] and years: newSeconds -= values[5]; valuesgot["years"] += 1
		elif newSeconds >= values[4] and months: newSeconds -= values[4]; valuesgot["months"] += 1
		elif newSeconds >= values[3] and weeks: newSeconds -= values[3]; valuesgot["weeks"] += 1
		elif newSeconds >= values[2] and days: newSeconds -= values[2]; valuesgot["days"] += 1
		elif newSeconds >= values[1] and hours: newSeconds -= values[1]; valuesgot["hours"] += 1
		elif newSeconds >= values[0] and minutes: newSeconds -= values[0]; valuesgot["minutes"] += 1
		else: valuesgot["seconds"] += newSeconds; newSeconds = 0; break
	for index, key in enumerate(valuesgot):
		if valuesgot[key] != 0:
			if len(stringslocal[index]) > valuesgot[key]: string.append(str(valuesgot[key]) + " " + stringslocal[index][valuesgot[key] - 1])
			else: string.append(str(valuesgot[key]) + " " + stringslocal[index][len(stringslocal[index]) - 1])
	if len(string) == 0: string.append("0 секунд")
	newStr = []
	for fstring in string:
		if maxCount > 0: newStr.append(fstring); maxCount -= 1
		else: break
	return ", ".join(newStr)

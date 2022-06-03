# coding: utf-8

from aiogram.types import InputFile
from typing import Literal
import aiohttp
import random
import re
import io
import os



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
	Возвращает первое доступное значение из словаря.
	"""

	for key in keys:
		if hasattr(cls, key):
			return cls.__dict__.get(key)

	return default

def isURL(url: str) -> bool:
	"""
	Проверяет, является ли строка URL или нет.
	"""

	return re.match(r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$", url) is not None

_bytes = bytes
class File:
	"""
	Класс, отображающий как файл.
	"""

	url: str | None
	path: str | None
	aiofile: InputFile | None
	bytes: _bytes | None
	filename: str | None

	type: Literal["photo", "sticker", "voice"]

	ready: bool = False

	def __init__(self, path_url_bytes_file: str | InputFile | io.IOBase | _bytes, file_type: Literal["photo", "sticker", "voice"] = "photo") -> None:
		self.type = file_type

		self.url = None
		self.path = None
		self.aiofile = None
		self.bytes = None
		self.filename = None

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
					self.filename = response.headers.get("Content-Disposition", "filename=unknown").split("filename=")[-1].strip('"')[-1]
		elif self.path:
			assert os.path.exists(self.path), f"Файл {self.path} не существует в системе"

			self.bytes = open(self.path, "rb").read()
			self.filename = os.path.basename(self.path)

		if self.bytes and not self.aiofile:
			self.aiofile = InputFile(io.BytesIO(self.bytes))


		self.ready = True
		return self

	def __str__(self) -> str:
		return "<File class>"


def clamp(number: float, value_min: float, value_max: float) -> float:
	"""
	Ограничивает значение `number` в пределах `value_min` и `value_max`.
	"""

	return max(value_min, min(number, value_max))

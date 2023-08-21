# coding: utf-8

import base64
import gzip
import hashlib
import io
import os
import re
import time
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import User as TelegramUser
from cryptography.fernet import Fernet
from loguru import logger

from config import config


def get_timestamp() -> int:
	"""
	Возвращает текущее время в формате UNIX Timestamp.
	"""

	return int(time.time())

def get_bot_version() -> int:
	"""
	Возвращает версию бота.
	"""

	return 2

def parse_str_boolean(value: str | bool) -> bool:
	"""
	Парсит строку в булевое значение.

	:param value: Строка, которую нужно распарсить.
	"""

	if isinstance(value, bool):
		return value
	elif value.lower().strip() in ["true", "1", "yes", "да"]:
		return True
	elif value.lower().strip() in ["false", "0", "no", "нет"]:
		return False
	else:
		raise Exception(f"Неверное значение переменной: \"{value}\". Ожидалось значение \"Yes\", \"No\", \"True\" или \"False\".")

def is_URL(url: str) -> bool:
	"""
	Проверяет, является ли строка URL или нет.

	:param url: Строка, которую нужно проверить.
	"""

	return re.match(r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$", url) is not None

def clamp(number: int | float, value_min: int | float, value_max: int | float) -> int | float:
	"""
	Ограничивает значение `number` в пределах `value_min` и `value_max`.

	:param number: Число, которое нужно ограничить.
	:param value_min: Минимальное значение.
	:param value_max: Максимальное значение.
	"""

	return max(value_min, min(number, value_max))

def traverse_dict(object: dict, *keys: str, default: Any = None):
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

def encrypt_with_env_key(input: str) -> str:
	"""
	Шифрует строку `input` ключём шифрования из `.env`-файла.

	:param input: Входная строка.
	"""

	# Проверяем, есть ли у нас ключ для шифрования в .env-файле:
	if not config.token_encryption_key:
		return input

	# Ключ шифрования есть, тогда шифруем:
	return encrypt_with_key(input, config.token_encryption_key.get_secret_value() + os.environ.get("token_encryption_key2", ""))

def decrypt_with_env_key(input: str) -> str:
	"""
	Расшифровывает строку `input` ключём шифрования из `.env`-файла.

	:param input: Входная строка.
	"""

	# Проверяем, есть ли у нас ключ для шифрования в .env-файле:
	if not config.token_encryption_key:
		return input

	# Ключ шифрования есть, тогда расшифровываем:
	return decrypt_with_key(input, config.token_encryption_key.get_secret_value() + os.environ.get("token_encryption_key2", ""))

def encrypt_with_key(input: str, key: str) -> str:
	"""
	Шифрует строку `input` с ключём `key`.

	:param input: Входная строка.
	:param key: Ключ шифрования.
	"""

	hlib = hashlib.md5()
	hlib.update(key.encode())

	return Fernet(base64.urlsafe_b64encode(hlib.hexdigest().encode())).encrypt(input.encode()).decode()

def decrypt_with_key(input: str, key: str) -> str:
	"""
	Расшифровывает строку `input` с ключём `key`.

	:param input: Входная строка.
	:param key: Ключ шифрования.
	"""

	hlib = hashlib.md5()
	hlib.update(key.encode())

	return Fernet(base64.urlsafe_b64encode(hlib.hexdigest().encode())).decrypt(input.encode()).decode()

def md5_hash(input: str) -> str:
	"""
	Выдаёт MD5-хэш строки.

	:param input: Входная строка.
	"""

	return hashlib.md5(input.encode()).hexdigest()

def sha256_hash(input: str) -> str:
	"""
	Выдаёт SHA256-хэш строки.

	:param input: Входная строка.
	"""

	return hashlib.sha256(input.encode()).hexdigest()

def seconds_to_userfriendly_string(seconds, max=2, minutes=True, hours=True, days=True, weeks=False, months=False, years=False, decades=False):
	"""
	Преобразовывает время, отображённое в секундах, как строку вида "5 часов, 17 секунд".

	:param seconds: Количество секунд.
	:param max: Максимальное количество единиц измерения времени, которые будут отображены в строке.
	:param minutes: Отображать ли минуты.
	:param hours: Отображать ли часы.
	:param days: Отображать ли дни.
	:param weeks: Отображать ли недели.
	:param months: Отображать ли месяцы.
	:param years: Отображать ли годы.
	:param decades: Отображать ли десятилетия.
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

def get_telegram_logging_info(user: TelegramUser | None, use_url: bool = False) -> str:
	"""
	Возвращает строку с информацией о пользователе для логирования. Используется в случае каких-либо ошибок для логирования.

	Пример вывода функции: `Full user name (@username, ID 123456)`

	:param user: Пользователь, о котором нужно получить информацию.
	:param use_url: Использовать ли ссылку на профиль пользователя вместо формата `@username`.
	"""

	if user is None:
		return "Unknown Telegram user"

	if user.username is None:
		return f"{user.full_name} (ID {user.id})"

	username_or_link = f"https://t.me/{user.username}" if use_url else f"@{user.username}"

	return f"{user.full_name} ({username_or_link}, ID {user.id})"

def telegram_safe_str(input: str) -> str:
	"""
	Возвращает копию строки, являющаяся «безопасной» для отправки как сообщение в Telegram.

	:param input: Входная строка.
	"""

	return input.replace("<br>", "\n")

async def convert_to_tgs_sticker(json_animation: bytes) -> bytes:
	"""
	Конвертирует анимацию в формате JSON (lottie) в TGS-стикер.

	:param json_animation: Содержимое JSON-файла с lottie-анимацией.
	"""

	# Убеждаемся, что в json_animation есть ключ "tgs".
	if b"\"tgs\":" not in json_animation:
		json_animation = json_animation.replace(
			b"\"v\":",
			b"\"tgs\":1,\"v\":"
		)

	# Создаём .tgs-архив (который на самом деле является .gz-архивом) из JSON-файла.
	gzip_file = io.BytesIO()

	# FIXME: По неясной причине, данный код возвращает нерабочий (непринимаемый Telegram)
	# .tgs-файл. Что бы я не делал, Telegram не хочет воспринимать файл за .tgs-стикер.
	# Что примечательно, при создании файла при помощи 7z, всё работает нормально.
	with gzip.GzipFile(fileobj=gzip_file, mode="wb", compresslevel=5) as gzipped_file:
		gzipped_file.write(json_animation)

	# Возвращаем байты .gz-архива.
	return gzip_file.getvalue()

class CodeTimer:
	"""
	Небольшая утилита, которая позволяет измерять время выполнения блока кода.
	"""

	message: str
	"""Сообщение, которое будет выведено в лог после выполнения блока кода."""

	def __init__(self, message: str = "Времени заняло: {time}с") -> None:
		"""
		Инициализирует данный класс.

		:param message: Сообщение, которое будет выведено в лог после выполнения блока кода. `{time}` - время выполнения блока кода.
		"""

		self.message = message

	def __enter__(self):
		self.start_time = time.perf_counter()

		return self

	def __exit__(self, exc_type, exc_value, traceback):
		logger.debug(self.message, time=time.perf_counter() - self.start_time)

def get_bot_username() -> str:
	"""
	Возвращает username бота.
	"""

	from telegram import bot


	assert bot.username

	return bot.username

def create_command_url(command: str) -> str:
	"""
	Возвращает строку, которую стоит использовать внутри тэга `<a>` для вызова команды `command`.

	:param command: Команда, которую нужно вызвать.
	"""

	username = get_bot_username()

	if command.startswith("/"):
		command = command[1:]

	deeplink = base64.b64encode(command.encode()).decode()

	# deeplink = html.escape(command)
	if len(deeplink) > 64:
		raise ValueError(f"Длина команды не может превышать 64 символа")

	return f"https://t.me/{username}?start={deeplink}"

def replace_placeholders(input: str) -> str:
	"""
	Возвращает копию строки с заменёнными placeholder'ами вида `{{something}}`.

	:param input: Входная строка.
	"""

	from api import TelehooperAPI


	return TelehooperAPI.get_settings().replace_placeholders(input)

def is_useful_exception(exc: Exception) -> bool:
	"""
	Метод для проверки на 'полезность' исключения. Если это исключения типа "Message Not Modified" или подобное, то данный метод возвращает `False`, в ином случае возвращает `True`.

	:param exc: Исключение.
	"""

	ignore_errors = ["message is not modified"]

	if isinstance(exc, TelegramAPIError):
		message = exc.message.lower()

		for error in ignore_errors:
			if error not in message:
				continue

			return False

	return True

def compact_name(input: str) -> str:
	"""
	Превращает имя человека в формате `Имя Фамилия` в формат `Имя Ф.`.

	:param input: Входная строка.
	"""

	if " " not in input:
		return input

	first_name, last_name = input.split(" ", 1)

	return f"{first_name} {last_name[0]}."

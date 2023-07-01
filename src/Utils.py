# coding: utf-8

import base64
import hashlib
import re
import time
from typing import Any

from aiogram.types import User as TelegramUser
from cryptography.fernet import Fernet

from config import config


DEBUG: bool = False

def get_timestamp() -> int:
	"""
	Возвращает текущее время в формате UNIX Timestamp.
	"""

	return int(time.time())

def get_bot_version() -> int:
	"""
	Возвращает версию бота.
	"""

	return 1

def parse_str_boolean(value: str | bool) -> bool:
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

def is_URL(url: str) -> bool:
	"""
	Проверяет, является ли строка URL или нет.
	"""

	return re.match(r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$", url) is not None

def clamp(number: int | float, value_min: int | float, value_max: int | float) -> int | float:
	"""
	Ограничивает значение `number` в пределах `value_min` и `value_max`.
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
	"""

	# Проверяем, есть ли у нас ключ для шифрования в .env-файле:
	if not config.token_encryption_key:
		# Ключа нет, не шифруем, возвращаем такое же значение.

		return input


	# Ключ шифрования есть, тогда шифруем:
	return Fernet(config.token_encryption_key.get_secret_value()).encrypt(input.encode()).decode()

def decrypt_with_env_key(input: str) -> str:
	"""
	Расшифровывает строку `input` ключём шифрования из `.env`-файла.
	"""

	# Проверяем, есть ли у нас ключ для шифрования в .env-файле:
	if not config.token_encryption_key:
		# Ключа нет, не шифруем, возвращаем такое же значение.

		return input


	# Ключ шифрования есть, тогда расшифровываем:
	return Fernet(config.token_encryption_key.get_secret_value()).decrypt(input.encode()).decode()

def encrypt_with_key(input: str, key: str) -> str:
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

def decrypt_with_key(input: str, key: str) -> str:
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

def md5_hash(input: str) -> str:
	"""
	Выдаёт MD5-хэш строки.
	"""

	return hashlib.md5(input.encode()).hexdigest()

def sha256_hash(input: str) -> str:
	"""
	Выдаёт SHA256-хэш строки.
	"""

	return hashlib.sha256(input.encode()).hexdigest()

def seconds_to_userfriendly_string(seconds, max=2, minutes=True, hours=True, days=True, weeks=False, months=False, years=False, decades=False):
	"""
	Преобразовывает время, отображённое в секундах, как строку вида "5 часов, 17 секунд".
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
	"""

	if user is None:
		return "Unknown Telegram user"

	if user.username is None:
		return f"{user.full_name} (ID {user.id})"

	username_or_link = f"https://t.me/{user.username}" if use_url else f"@{user.username}"

	return f"{user.full_name} ({username_or_link}, ID {user.id})"

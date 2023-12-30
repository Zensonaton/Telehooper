# coding: utf-8

import asyncio
import base64
import gzip
import hashlib
import io
import os
import re
import subprocess
import time
import uuid

import psutil
from aiogram.exceptions import TelegramAPIError
from aiogram.types import User as TelegramUser
from cryptography.fernet import Fernet
from loguru import logger

from config import config
from consts import (MAX_DOWNLOAD_FILE_SIZE_BYTES,
					MAX_LOCAL_SERVER_DOWNLOAD_FILE_SIZE_BYTES,
					MAX_LOCAL_SERVER_UPLOAD_FILE_SIZE_BYTES,
					MAX_UPLOAD_FILE_SIZE_BYTES)


COMMIT_HASH = None

def get_timestamp() -> int:
	"""
	Возвращает текущее время в формате UNIX Timestamp.
	"""

	return int(time.time())

def get_uuid() -> str:
	"""
	Возвращает случайный UUID v4.
	"""

	return str(uuid.uuid4())

def get_bot_version() -> int:
	"""
	Возвращает версию бота, используемая при хранении некоторых объектов в БД.
	"""

	return 3

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

	def _inner() -> bytes:
		"""
		Внутренний метод для преобразования Lottie-анимации (.json) в .tgs (.gz)-архив. Вызывается в отдельном thread'е.
		"""

		gzip_file = io.BytesIO()

		with gzip.GzipFile(fileobj=gzip_file, mode="wb", compresslevel=5) as gzipped_file:
			gzipped_file.write(json_animation)

		return gzip_file.getvalue()

	return await asyncio.to_thread(_inner)

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

def time_since(timestamp: int) -> int:
	"""
	Возвращает количество секунд, прошедшее с момента `timestamp`.

	:param timestamp: Время в формате UNIX Timestamp.
	"""

	return get_timestamp() - timestamp

async def get_commit_hash() -> str | None:
	"""
	Возвращает строку хэша последнего коммита, либо None, если что-то пошло не так (например, `.git` не инициализирован).
	"""

	global COMMIT_HASH


	if COMMIT_HASH is not None:
		return COMMIT_HASH

	try:
		proc = await asyncio.create_subprocess_shell(
			"git rev-parse --short HEAD",
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
		)

		stdout, stderr = await proc.communicate()

		if proc.returncode != 0:
			return None

		COMMIT_HASH = stdout.decode().strip()

		return COMMIT_HASH
	except Exception as e:
		return None

def get_ram_usage() -> float:
	"""
	Возвращает количество использованной ботом оперативной памяти.

	Возвращает значение в мегабайтах.
	"""

	return psutil.Process().memory_info().rss / 1_000_000

def get_minibot_tokens() -> list[str]:
	"""
	Возвращает список Telegram Bot API токенов у миниботов.
	"""

	return config.minibot_tokens.get_secret_value().replace(" ", "").split(",")

async def convert_mp4_to_gif(data: bytes) -> bytes:
	"""
	Конвертирует передаваемые bytes .mp4-видео как .gif.
	"""

	assert config.ffmpeg_path, "В .env-файле не указан путь к ffmpeg"

	command = [
		config.ffmpeg_path,
		"-i", "pipe:0",
		"-vf", "fps=10,scale=320:-1:flags=lanczos",
		"-c:v", "gif",
		"-f", "gif",
		"pipe:1"
	]

	process = await asyncio.create_subprocess_exec(
		*command,
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE
	)

	assert process.stdin, "stdin отсутствует"

	# Отправляем ffmpeg всё байтовое содержимое видео.
	process.stdin.write(data)
	process.stdin.close()

	# Получаем готовый .gif-файл.
	gif_data, error_output = await process.communicate()

	if process.returncode != 0:
		raise Exception(f"Ошибка конвертации ffmpeg: {error_output.decode('utf-8')}")

	return gif_data

def is_local_bot_api() -> bool:
	"""
	Возвращает True, если используется Local Bot API.
	"""

	return bool(config.telegram_local_api_url and config.telegram_local_file_url)

def max_upload_bytes() -> int:
	"""
	Возвращает максимальный размер файла в байтах, который используется для выгрузки файла в Telegram. Данное значение зависит от того, используется ли Local Bot API или нет.
	"""

	return MAX_LOCAL_SERVER_UPLOAD_FILE_SIZE_BYTES if is_local_bot_api() else MAX_UPLOAD_FILE_SIZE_BYTES

def max_download_bytes() -> int:
	"""
	Возвращает максимальный размер файла в байтах, который используется для загрузки файла из Telegram. Данное значение зависит от того, используется ли Local Bot API или нет.
	"""

	return MAX_LOCAL_SERVER_DOWNLOAD_FILE_SIZE_BYTES if is_local_bot_api() else MAX_DOWNLOAD_FILE_SIZE_BYTES

def extract_url(input: str) -> str | None:
	"""
	Извлекает самую первую ссылку из входной строки.

	:param input: Входная строка, из которой будет извлечён URL.
	"""

	match = re.search(r"https?://\S+", input)

	return match.group() if match else None

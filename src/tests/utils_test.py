# coding: utf-8

from time import sleep

import pytest

import utils


def test_getTimestamp():
	"""
	`get_timestamp()` возвращает текущий timestamp.
	"""

	assert isinstance(utils.get_timestamp(), int)

	time = utils.get_timestamp()
	sleep(1)
	assert utils.get_timestamp() > time

def test_getBotVersion():
	"""
	`get_bot_version()` возвращает версию бота.
	"""

	assert isinstance(utils.get_bot_version(), int)

def test_parseStrAsBoolean():
	"""
	`parse_str_boolean()` парсит строку в булевое значение, и в случае другого значения кидает ошибку.
	"""

	assert utils.parse_str_boolean("True") == True
	assert isinstance(utils.parse_str_boolean("True"), bool)
	assert utils.parse_str_boolean("False") == False
	assert utils.parse_str_boolean("Yes") == True
	assert utils.parse_str_boolean("No") == False
	assert utils.parse_str_boolean("0") == False
	assert utils.parse_str_boolean("1") == True
	assert utils.parse_str_boolean(True) == True
	assert utils.parse_str_boolean("tRue") == True
	assert utils.parse_str_boolean("fAlse") == False
	assert utils.parse_str_boolean(" True ") == True
	assert utils.parse_str_boolean("	False	") == False

	with pytest.raises(Exception):
		utils.parse_str_boolean(" Fake Value!")

def test_isURL():
	"""
	`is_URL()` проверяет, является ли строка ссылкой.
	"""

	assert utils.is_URL("https://vk.com/") == True
	assert utils.is_URL("https://vk.com") == True
	assert utils.is_URL("file://hi.com") == False
	assert utils.is_URL("C:/Windows/hi") == False
	assert utils.is_URL("C:\\Windows\\hi") == False
	assert utils.is_URL("/home/hi") == False

def test_clamp():
	"""
	`clamp()` ограничивает значение в заданных пределах.
	"""

	assert utils.clamp(number=0, value_min=0, value_max=1) == 0
	assert utils.clamp(number=0, value_min=1, value_max=0) == 1
	assert utils.clamp(number=1, value_min=0, value_max=0) == 0
	assert utils.clamp(number=2, value_min=0, value_max=0) == 0
	assert utils.clamp(number=2, value_min=-1, value_max=2) == 2
	assert utils.clamp(number=-5, value_min=-1, value_max=2) == -1

def test_encryptAndDecrypt():
	"""
	Тестирует шифрование и дешифровку.
	"""

	testString = "Hello, World!"
	pwd = "mypassword"

	encrypted = utils.encrypt_with_key(testString, pwd)
	decrypted = utils.decrypt_with_key(encrypted, pwd)

	assert testString == decrypted

def test_md5Hash():
	"""
	Тестирует хеширование MD5.
	"""

	testString = "Hello, World!"

	assert utils.md5_hash(testString) == utils.md5_hash(testString)
	assert utils.md5_hash(testString) != utils.md5_hash(testString + "!")
	assert len(utils.md5_hash(testString)) == 32

def test_sha256Hash():
	"""
	Тестирует хеширование SHA256.
	"""

	testString = "Hello, World!"

	assert utils.sha256_hash(testString) == utils.sha256_hash(testString)
	assert utils.sha256_hash(testString) != utils.sha256_hash(testString + "!")
	assert len(utils.sha256_hash(testString)) == 64

def test_secondsToUserfriendlyString():
	"""
	`seconds_to_userfriendly_string()` конвертирует секунды в строку вида "1 день, 5 минут".
	"""

	assert utils.seconds_to_userfriendly_string(0) == "0 секунд"
	assert utils.seconds_to_userfriendly_string(1) == "1 секунда"
	assert utils.seconds_to_userfriendly_string(2) == "2 секунды"
	assert utils.seconds_to_userfriendly_string(5) == "5 секунд"
	assert utils.seconds_to_userfriendly_string(10) == "10 секунд"
	assert utils.seconds_to_userfriendly_string(11) == "11 секунд"
	assert utils.seconds_to_userfriendly_string(60) == "1 минута"
	assert utils.seconds_to_userfriendly_string(61) == "1 минута, 1 секунда"
	assert utils.seconds_to_userfriendly_string(62) == "1 минута, 2 секунды"
	assert utils.seconds_to_userfriendly_string(65) == "1 минута, 5 секунд"
	assert utils.seconds_to_userfriendly_string(120) == "2 минуты"
	assert utils.seconds_to_userfriendly_string(60 * 60 * 24 * 30) == "30 дней"
	assert utils.seconds_to_userfriendly_string(60 * 60 * 24 * 365) == "365 дней"
	assert utils.seconds_to_userfriendly_string(60 * 60 * 24 * 365, max=1, years=True) == "1 год"

def test_telegramSafeStr():
	"""
	`telegram_safe_str()` заменяет символы, которые могут вызвать ошибку в Telegram API.
	"""

	assert utils.telegram_safe_str("Hello, World!") == "Hello, World!"
	assert utils.telegram_safe_str("Test!<br>Newline!") == "Test!\nNewline!"

def test_compactName():
	"""
	`compact_name()` возвращает компактное имя.
	"""

	assert utils.compact_name("Иван Петров") == "Иван П."

def test_timeSince():
	"""
	`time_since()` возвращает количество секунд, прошедшее с определённого момента.
	"""

	time = utils.get_timestamp()

	assert utils.time_since(time) == 0
	assert utils.time_since(time - 1) == 1
	sleep(1)
	assert utils.time_since(time) == 1


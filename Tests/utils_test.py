# coding: utf-8

from unittest.mock import patch, mock_open
from src import Utils
import unittest

class TestUtils(unittest.TestCase):

	def test_parseStrAsBoolean(self):
		# parseStrAsBoolean() парсит строку в булевое значение, и в случае другого значения кидает ошибку.

		self.assertEqual(Utils.parseStrAsBoolean("True"), True)
		self.assertEqual(Utils.parseStrAsBoolean("False"), False)

		self.assertEqual(Utils.parseStrAsBoolean("Yes"), True)
		self.assertEqual(Utils.parseStrAsBoolean("No"), False)

		self.assertEqual(Utils.parseStrAsBoolean("0"), False)
		self.assertEqual(Utils.parseStrAsBoolean("1"), True)

		self.assertEqual(Utils.parseStrAsBoolean(True), True)

		self.assertEqual(Utils.parseStrAsBoolean("tRue"), True)
		self.assertEqual(Utils.parseStrAsBoolean("fAlse"), False)

		self.assertEqual(Utils.parseStrAsBoolean(" True "), True)
		self.assertEqual(Utils.parseStrAsBoolean("	False	"), False)

		self.assertRaises(Exception, Utils.parseStrAsBoolean, " Fake Value!")

	def test_extractAccessTokenFromFullURL(self):
		# extractAccessTokenFromFullURL() извлекает ACCESS_TOKEN из URL.

		self.assertEqual(Utils.extractAccessTokenFromFullURL("https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&user_id=123456789"), "123456789")
		self.assertEqual(Utils.extractAccessTokenFromFullURL("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=123456789"), "aaaaaaaaa")
		self.assertEqual(Utils.extractAccessTokenFromFullURL("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=123456789&other_param=123456789"), "aaaaaaaaa")

		self.assertRaises(Exception, Utils.extractAccessTokenFromFullURL, "https://oauth.vk.com/blank.html#access_token=&expires_in=86400&user_id=123456789&other_param=123456789&another_param=123456789")
		self.assertRaises(Exception, Utils.extractAccessTokenFromFullURL, "https://oauth.vk.com/blank.html#&expires_in=86400&user_id=123456789&other_param=123456789&another_param=123456789")

	def test_extractUserIDFromFullURL(self):
		# extractUserIDFromFullURL() извлекает USER_ID из URL.

		self.assertEqual(Utils.extractUserIDFromFullURL("https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&user_id=123456789"), 123456789)
		self.assertEqual(Utils.extractUserIDFromFullURL("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=0"), 0)
		self.assertEqual(Utils.extractUserIDFromFullURL("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=123456789&other_param=123"), 123456789)

		self.assertRaises(Exception, Utils.extractUserIDFromFullURL, "https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&user_id=&other_param=123456789")
		self.assertRaises(Exception, Utils.extractUserIDFromFullURL, "https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&other_param=123")

	def test_generateVKRandomID(self):
		# generateVKRandomID() генерирует случайный ID для отправки сообщения ВКонтакте.

		self.assertIsInstance(Utils.generateVKRandomID(), int)

	def test_getFirstAvailableValueFromClass(self):
		# Тестирует функцию getFirstAvailableValueFromClass, которая пытается получить первое доступное значение из класса.

		class TestClass:
			def __init__(self):
				self.value_1 = "bad"
				self.value_2 = "bad"
				self.value_3 = "bad"
				self.value_4 = "bad"
				self.value_5 = "good"
				self.value_6 = "bad"

		testClass = TestClass()

		self.assertEqual(Utils.getFirstAvailableValueFromClass(testClass, "value_5"), "good")
		self.assertEqual(Utils.getFirstAvailableValueFromClass(testClass, "value_6", "value_5"), "bad")
		self.assertEqual(Utils.getFirstAvailableValueFromClass(testClass), None)
		self.assertEqual(Utils.getFirstAvailableValueFromClass(testClass, "non_existing_value"), None)
		self.assertEqual(Utils.getFirstAvailableValueFromClass(testClass, "non_existing_value", default=True), True)

	def test_isURL(self):
		# isURL() проверяет, является ли строка ссылкой.

		self.assertEqual(Utils.isURL("https://vk.com/"), True)
		self.assertEqual(Utils.isURL("https://vk.com"), True)
		self.assertEqual(Utils.isURL("file://hi.com"), False)
		self.assertEqual(Utils.isURL("C:/Windows/hi"), False)
		self.assertEqual(Utils.isURL("C:\\Windows\\hi"), False)
		self.assertEqual(Utils.isURL("/home/hi"), False)

	def test_clamp(self):
		# clamp() ограничивает значение в заданных пределах.

		self.assertEqual(Utils.clamp(number=0, value_min=0, value_max=1), 0)
		self.assertEqual(Utils.clamp(number=0, value_min=1, value_max=0), 1)
		self.assertEqual(Utils.clamp(number=1, value_min=0, value_max=0), 0)
		self.assertEqual(Utils.clamp(number=2, value_min=0, value_max=0), 0)
		self.assertEqual(Utils.clamp(number=2, value_min=-1, value_max=2), 2)
		self.assertEqual(Utils.clamp(number=-5, value_min=-1, value_max=2), -1)

	def test_traverseDict(self):
		# traverseDict() ищет значение из dict с N-ным количеством ключей.

		testDict = {
			"hi": {
				"test": {
					"foo": {
						"bar": True
					}
				}
			}
		}

		self.assertEqual(Utils.traverseDict(testDict, "hi", "test", "foo", "bar"), True)
		self.assertEqual(Utils.traverseDict(testDict, "hi", "test", "foo"), {"bar": True})
		self.assertEqual(Utils.traverseDict(testDict, "hi", "test", "foo", "doesnotexists"), None)
		self.assertEqual(Utils.traverseDict(testDict, "hi", "test", "foo", "bar", "doesnotexists"), None)

	def test_getDictValuesByKeyPrefixes(self):
		# getDictValuesByKeyPrefixes() выдаёт все значения из dict, ключи которого совпадают с данным функции префиксом.

		testDict = {
			"hi": True,
			"something": {"foo": "bar"},
			"!first": False,
			"!second": False,
			"???": ["foo"],
			True: "False"
		}

		self.assertEqual(Utils.getDictValuesByKeyPrefixes(testDict, "!"), {"!first": False, "!second": False})
		self.assertEqual(Utils.getDictValuesByKeyPrefixes(testDict, "nonexist"), {})
		self.assertEqual(Utils.getDictValuesByKeyPrefixes(testDict, "?"), {"???": ["foo"]})
		self.assertEqual(Utils.getDictValuesByKeyPrefixes(testDict, "???"), {"???": ["foo"]})

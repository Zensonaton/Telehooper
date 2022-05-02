# coding: utf-8

import unittest
from src import Utils

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

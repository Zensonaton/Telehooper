# coding: utf-8

import unittest

from ..src.services.vk import utils


class TestUtils(unittest.TestCase):
	def test_extractAccessTokenFromFullURL(self):
		# extractAccessTokenFromFullURL() извлекает ACCESS_TOKEN из URL.

		self.assertEqual(utils.extract_access_token_from_url("https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&user_id=123456789"), "123456789")
		self.assertEqual(utils.extract_access_token_from_url("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=123456789"), "aaaaaaaaa")
		self.assertEqual(utils.extract_access_token_from_url("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=123456789&other_param=123456789"), "aaaaaaaaa")

		self.assertRaises(Exception, utils.extract_access_token_from_url, "https://oauth.vk.com/blank.html#access_token=&expires_in=86400&user_id=123456789&other_param=123456789&another_param=123456789")
		self.assertRaises(Exception, utils.extract_access_token_from_url, "https://oauth.vk.com/blank.html#&expires_in=86400&user_id=123456789&other_param=123456789&another_param=123456789")

	def test_extractUserIDFromFullURL(self):
		# extractUserIDFromFullURL() извлекает USER_ID из URL.

		self.assertEqual(utils.extract_user_id_from_url("https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&user_id=123456789"), 123456789)
		self.assertEqual(utils.extract_user_id_from_url("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=0"), 0)
		self.assertEqual(utils.extract_user_id_from_url("https://oauth.vk.com/blank.html#access_token=aaaaaaaaa&expires_in=86400&user_id=123456789&other_param=123"), 123456789)

		self.assertRaises(Exception, utils.extract_user_id_from_url, "https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&user_id=&other_param=123456789")
		self.assertRaises(Exception, utils.extract_user_id_from_url, "https://oauth.vk.com/blank.html#access_token=123456789&expires_in=86400&other_param=123")

	def test_generateVKRandomID(self):
		# generateVKRandomID() генерирует случайный ID для отправки сообщения ВКонтакте.

		self.assertIsInstance(utils.random_id(), int)

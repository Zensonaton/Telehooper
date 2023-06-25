# coding: utf-8

import unittest

from ..src import utils


class TestUtils(unittest.TestCase):
	def test_parseStrAsBoolean(self):
		# parseStrAsBoolean() парсит строку в булевое значение, и в случае другого значения кидает ошибку.

		self.assertEqual(utils.parse_str_boolean("True"), True)
		self.assertEqual(utils.parse_str_boolean("False"), False)

		self.assertEqual(utils.parse_str_boolean("Yes"), True)
		self.assertEqual(utils.parse_str_boolean("No"), False)

		self.assertEqual(utils.parse_str_boolean("0"), False)
		self.assertEqual(utils.parse_str_boolean("1"), True)

		self.assertEqual(utils.parse_str_boolean(True), True)

		self.assertEqual(utils.parse_str_boolean("tRue"), True)
		self.assertEqual(utils.parse_str_boolean("fAlse"), False)

		self.assertEqual(utils.parse_str_boolean(" True "), True)
		self.assertEqual(utils.parse_str_boolean("	False	"), False)

		self.assertRaises(Exception, utils.parse_str_boolean, " Fake Value!")

	def test_isURL(self):
		# isURL() проверяет, является ли строка ссылкой.

		self.assertEqual(utils.is_URL("https://vk.com/"), True)
		self.assertEqual(utils.is_URL("https://vk.com"), True)
		self.assertEqual(utils.is_URL("file://hi.com"), False)
		self.assertEqual(utils.is_URL("C:/Windows/hi"), False)
		self.assertEqual(utils.is_URL("C:\\Windows\\hi"), False)
		self.assertEqual(utils.is_URL("/home/hi"), False)

	def test_clamp(self):
		# clamp() ограничивает значение в заданных пределах.

		self.assertEqual(utils.clamp(number=0, value_min=0, value_max=1), 0)
		self.assertEqual(utils.clamp(number=0, value_min=1, value_max=0), 1)
		self.assertEqual(utils.clamp(number=1, value_min=0, value_max=0), 0)
		self.assertEqual(utils.clamp(number=2, value_min=0, value_max=0), 0)
		self.assertEqual(utils.clamp(number=2, value_min=-1, value_max=2), 2)
		self.assertEqual(utils.clamp(number=-5, value_min=-1, value_max=2), -1)

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

		self.assertEqual(utils.traverse_dict(testDict, "hi", "test", "foo", "bar"), True)
		self.assertEqual(utils.traverse_dict(testDict, "hi", "test", "foo"), {"bar": True})
		self.assertEqual(utils.traverse_dict(testDict, "hi", "test", "foo", "doesnotexists"), None)
		self.assertEqual(utils.traverse_dict(testDict, "hi", "test", "foo", "bar", "doesnotexists"), None)

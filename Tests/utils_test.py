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

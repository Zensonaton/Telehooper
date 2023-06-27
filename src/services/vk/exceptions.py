# coding: utf-8

class BaseVKAPIException(Exception):
	"""
	Базовое исключение для всех ошибок, связанных с API ВКонтакте.
	"""

	error_code: int
	message: str

	def __init__(self, error_code: int, message: str) -> None:
		"""
		Инициализация исключения.

		:param error_code: Код ошибки.
		:param message: Сообщение об ошибке.
		"""

		self.error_code = error_code
		self.message = message

class AccountDeactivatedException(BaseVKAPIException):
	"""
	Исключение, которое вызывается, если аккаунт ВКонтакте удалён, заморожен или заблокирован.
	"""

	def __init__(self, error_code: int = 3610, message: str = "Аккаунт удалён, заморожен или заблокирован.") -> None:
		"""
		Инициализация исключения.
		"""

		super().__init__(error_code=error_code, message=message)

# coding: utf-8

class BaseVKAPIException(Exception):
	"""
	Базовое исключение для всех ошибок, связанных с API ВКонтакте.
	"""

	error_code: int
	"""Код ошибки."""
	message: str
	"""Текст сообщения ошибки."""

	def __init__(self, error_code: int, message: str) -> None:
		"""
		Инициализация исключения.

		:param error_code: Код ошибки.
		:param message: Сообщение об ошибке.
		"""

		self.error_code = error_code
		self.message = message

	def __repr__(self) -> str:
		return f"<{self.__class__.__name__} error_code={self.error_code} message={self.message}>"

	def __str__(self) -> str:
		return f"[{self.error_code}] {self.message}"

class AccountDeactivatedException(BaseVKAPIException):
	"""
	Исключение, которое вызывается, если аккаунт ВКонтакте удалён, заморожен или заблокирован.
	"""

	def __init__(self, error_code: int = 3610, message: str = "Аккаунт удалён, заморожен или заблокирован.") -> None:
		"""
		Инициализация исключения.
		"""

		super().__init__(error_code=error_code, message=message)

class TokenRevokedException(BaseVKAPIException):
	"""
	Исключение, которое вызывается, если токен ВКонтакте был отозван владельцем страницы.
	"""

	def __init__(self, error_code: int = 5, message: str = "Токен ВКонтакте отозван.") -> None:
		"""
		Инициализация исключения.
		"""

		super().__init__(error_code=error_code, message=message)

class TooManyRequestsException(BaseVKAPIException):
	"""
	Исключение, которое вызывается, если API создал слишком много запросов за небольшой промежуток времени.
	"""

	def __init__(self, error_code: int = 6, message: str = "Слишком много действий в секунду.") -> None:
		"""
		Инициализация исключения.
		"""

		super().__init__(error_code=error_code, message=message)

class CaptchaException(BaseVKAPIException):
	"""
	Исключение, которое вызывается, если требуется ввод капчи.
	"""

	def __init__(self, error_code: int = 14, message: str = "Требуется ввод капчи.") -> None:
		"""
		Инициализация исключения.
		"""

		super().__init__(error_code=error_code, message=message)

class AccessDeniedException(BaseVKAPIException):
	"""
	Исключение, которое вызывается, если доступ к методу запрещён.
	"""

	def __init__(self, error_code: int = 15, message: str = "Доступ запрещён.") -> None:
		"""
		Инициализация исключения.
		"""

		super().__init__(error_code=error_code, message=message)

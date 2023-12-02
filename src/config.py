# coding: utf-8

from pydantic import BaseSettings, Field, SecretStr

import consts


class Configuration(BaseSettings):
	"""
	Конфигурация бота, загружающаяся с `.env`-файла.
	"""

	telegram_token: SecretStr = Field(..., description="Токен для Telegram-бота, который можно получить у @BotFather", env="telegram_token")
	"""Токен для Telegram-бота, который можно получить у @BotFather."""
	couchdb_name: str = Field(..., description="Название базы данных CouchDB", env="couch_db_database")
	"""Название базы данных CouchDB."""
	couchdb_host: str = Field("http://localhost:5984", description="Хост базы данных CouchDB", env="couch_db_host")
	"""Хост базы данных CouchDB."""
	couchdb_user: str = Field(..., description="Пользователь базы данных CouchDB", env="couch_db_user")
	"""Пользователь базы данных CouchDB."""
	couchdb_password: SecretStr = Field(..., description="Пароль базы данных CouchDB", env="couch_db_password")
	"""Пароль базы данных CouchDB."""
	token_encryption_key: SecretStr = Field(..., description="Ключ шифрования токенов в базе данных", env="token_encryption_key", min_length=6)
	"""Ключ шифрования токенов в базе данных."""
	vkbot_notifier_id: int = Field(213024897, description="ID VK группы, в которую будет отправляться сообщение для уведомление о подключении нового пользователя. Используй 0 для отключения.", env="vkbot_notifier_id")
	"""ID VK группы, в которую будет отправляться сообщение для уведомление о подключении нового пользователя. Используй 0 для отключения."""
	debug: bool = Field(False, description="Включает режим отладки", env="debug")
	"""Включает режим отладки."""

	class Config:
		env_file = ".env" if not consts.IS_TESTING else "src/tests/test.env"
		env_file_encoding = "utf-8"
		case_sensitive = False

config = Configuration() # type: ignore
"""Конфигурация бота, загружающаяся с `.env`-файла."""

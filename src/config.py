# coding: utf-8

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

import consts


class Configuration(BaseSettings):
	"""
	Конфигурация бота, загружающаяся с `.env`-файла.
	"""

	telegram_token: SecretStr = Field(..., description="Токен для Telegram-бота, который можно получить у @BotFather")
	"""Токен для Telegram-бота, который можно получить у @BotFather."""
	telegram_local_api_url: str | None = Field(None, description="URL для Local Bot API. Чаще всего используется `http://localhost:8081`")
	"""URL для Local Bot API. Чаще всего используется `http://localhost:8081`."""
	telegram_local_file_url: str | None = Field(None, description="URL для хранимых файлов Local Bot API. Чаще всего используется `http://localhost:8080`")
	"""URL для хранимых файлов Local Bot API. Чаще всего используется `http://localhost:8080`."""
	minibot_tokens: SecretStr = Field("", description="Список токенов для Telegram мини ботов, которые можно получить у @BotFather. Все эти токены должны разделяться запятой")
	"""Список токенов для Telegram мини ботов, которые можно получить у @BotFather. Все эти токены должны разделяться запятой."""

	couchdb_name: str = Field(..., description="Название базы данных CouchDB")
	"""Название базы данных CouchDB."""
	couchdb_host: str = Field("http://localhost:5984", description="Хост базы данных CouchDB")
	"""Хост базы данных CouchDB."""
	couchdb_user: str = Field(..., description="Пользователь базы данных CouchDB")
	"""Пользователь базы данных CouchDB."""
	couchdb_password: SecretStr = Field(..., description="Пароль базы данных CouchDB")
	"""Пароль базы данных CouchDB."""

	token_encryption_key: SecretStr = Field(..., description="Ключ шифрования токенов в базе данных", min_length=6)
	"""Ключ шифрования токенов в базе данных."""
	vkbot_notifier_id: int = Field(213024897, description="ID VK группы, в которую будет отправляться сообщение для уведомление о подключении нового пользователя. Используй 0 для отключения")
	"""ID VK группы, в которую будет отправляться сообщение для уведомление о подключении нового пользователя. Используй 0 для отключения."""

	ffmpeg_path: str | None = Field(None, description="Путь к binary ffmpeg. Используется для конвертации GIF из Telegram (которые на деле являются mp4-видео) в 'настоящие' GIF для сервисов")
	"""Путь к binary ffmpeg. Используется для конвертации GIF из Telegram (которые на деле являются mp4-видео) в 'настоящие' GIF для сервисов."""

	debug: bool = Field(False, description="Включает режим отладки")
	"""Включает режим отладки."""

	model_config = SettingsConfigDict(
		env_file=".env" if not consts.IS_TESTING else "src/tests/test.env",
		env_file_encoding="utf-8",
		case_sensitive = False,
		extra="allow"
	)

config = Configuration() # type: ignore
"""Конфигурация бота, загружающаяся с `.env`-файла."""

# coding: utf-8

from pydantic import BaseSettings, Field, SecretStr


class Configuration(BaseSettings):
	"""
	Конфигурация бота, загружающаяся с `.env`-файла.
	"""

	telegram_token: SecretStr = Field(..., description="Токен для Telegram-бота, который можно получить у @BotFather", env="telegram_token")

	couchdb_name: str = Field(..., description="Название базы данных CouchDB", env="couch_db_database")
	couchdb_host: str = Field("http://localhost:5984", description="Хост базы данных CouchDB", env="couch_db_host")
	couchdb_user: str = Field(..., description="Пользователь базы данных CouchDB", env="couch_db_user")
	couchdb_password: str = Field(..., description="Пароль базы данных CouchDB", env="couch_db_password")

	token_encryption_key: SecretStr = Field(..., description="Ключ шифрования токенов в базе данных", env="token_encryption_key", min_length=6)

	vkbot_notifier_id: int = Field(213024897, description="ID VK группы, в которую будет отправляться сообщение для уведомление о подключении нового пользователя. Используй 0 для отключения.", env="vkbot_notifier_id")


	debug: bool = Field(False, description="Включает режим отладки", env="debug")


	class Config:
		env_file = ".env"
		env_file_encoding = "utf-8"
		case_sensitive = False

config = Configuration() # type: ignore

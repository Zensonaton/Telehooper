# coding: utf-8

# Файл для соеденинения с MongoDB.

from __future__ import annotations

import os
import urllib.parse

from pymongo.mongo_client import MongoClient


def getDatabase(host: str = "localhost", port: int = 27017, user: str | None = None, pwd: str | None = None, auth_source: str | None = None) -> MongoClient:
	"""
	Пытается подключиться к MongoDB-базе данных.
	"""

	connectionUri = f"mongodb://{host}:{port}"
	if pwd and user and auth_source:
		connectionUri = f"mongodb://{user}:{urllib.parse.quote(pwd, safe='')}@{host}:{port}/?authSource={auth_source}"

	return MongoClient(connectionUri)

def getCollection(database: MongoClient, database_name: str, collection: str):
	"""
	Пытается подключиться к коллекции.
	"""

	return database[database_name][collection]

def getDefaultDatabase() -> MongoClient:
	"""
	Пытается автоматически вытащить все данные из .env файла и подключиться к базе данных.
	"""

	return getDatabase(
		host=os.environ["MONGODB_HOST"],
		port=int(os.environ["MONGODB_PORT"]),
		user=os.environ["MONGODB_USER"],
		pwd=os.environ["MONGODB_PWD"],
		auth_source=os.environ["MONGODB_DBNAME"]
	)

def getDefaultCollection():
	"""
	Пытается автоматически вытащить все данные из .env файла и подключиться к коллекции.
	"""

	return getCollection(
		database=getDefaultDatabase(),
		database_name=os.environ["MONGODB_DBNAME"],
		collection=os.environ["MONGODB_COLLECTION"]
	)

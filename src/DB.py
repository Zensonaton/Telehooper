# coding: utf-8

# Файл для соеденинения с MongoDB.

from __future__ import annotations

import os

import pymongo


def getDatabase(host: str = "localhost", port: int = 27017) -> pymongo.MongoClient:
	"""
	Пытается подключиться к MongoDB-базе данных.
	"""

	return pymongo.MongoClient(host, port)

def getCollection(database: pymongo.MongoClient, database_name: str, collection: str):
	"""
	Пытается подключиться к коллекции.
	"""

	return database[database_name][collection]

def getDefaultDatabase() -> pymongo.MongoClient:
	"""
	Пытается автоматически вытащить все данные из .env файла и подключиться к базе данных.
	"""

	return getDatabase(host=os.environ["MONGODB_HOST"], port=int(os.environ["MONGODB_PORT"]))

def getDefaultCollection():
	"""
	Пытается автоматически вытащить все данные из .env файла и подключиться к коллекции.
	"""

	return getCollection(
		database=getDefaultDatabase(),
		database_name=os.environ["MONGODB_DBNAME"],
		collection=os.environ["MONGODB_COLLECTION"]
	)

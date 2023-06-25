# coding: utf-8

import os

from aiocouch import CouchDB, Database, Document
from aiocouch.exception import NotFoundError
from aiogram import types
from loguru import logger

import utils
from config import config


couchdb: CouchDB | None = None
DB: Database | None = None

async def get_db(db_name: str | None = None, check_auth: bool = False, force_new: bool = False) -> Database:
	"""
	Возвращает объект для работы с базой данных.
	"""

	global DB, couchdb


	if db_name is None:
		db_name = config.couchdb_name

	if couchdb is None:
		couchdb = CouchDB(
			config.couchdb_host,
			user=config.couchdb_user,
			password=config.couchdb_password
		)


	if check_auth:
		await couchdb.check_credentials()

	if DB and not force_new:
		return DB

	try:
		DB = await couchdb[db_name]
	except NotFoundError:
		logger.warning(f"База данных \"{db_name}\" не была найдена, поэтому она была создана. Учтите, что вам **необходимо** должным образом защитить эту базу данных.")

		await couchdb.create(db_name)

		DB = await couchdb[db_name]


	return DB

async def get_user(user: types.User, create_by_default: bool = True) -> Document:
	"""
	Возвращает данные пользователя из базы данных.

	Если `create_by_default` равен `True`, то пользователь будет создан, если он не был найден, в противном случае будет вызвана ошибка.
	"""

	db = await get_db()

	id = str(user.id)

	try:
		return await db["user_" + id]
	except NotFoundError:
		if not create_by_default:
			raise NotFoundError(f"Пользователь с ID {id} не был найден в базе данных.")

		# Пользователь не был найден, поэтому мы создаем его.
		user_db = await db.create(
			"user_" + id,
			False,
			get_default_user(user)
		)
		await user_db.save()

		return user_db

async def get_global(create_by_default: bool = True) -> Document:
	"""
	Возвращает глобальную запись из БД.

	Если `create_by_default` равен `True`, то глобальная запись будет создана, если она не был найдена, в противном случае будет вызвана ошибка.
	"""

	db = await get_db()

	try:
		return await db["global"]
	except NotFoundError:
		if not create_by_default:
			raise NotFoundError(f"Глобальная запись не была найдена в базе данных.")

		# Глобальная запись не была найдена, поэтому мы создаем её.
		global_db = await db.create(
			"global",
			False,
			get_default_global()
		)
		await global_db.save()

		return global_db

def get_default_user(user: types.User, version: int = utils.get_bot_version()) -> dict:
	"""
	Возвращает шаблон пользователя для сохранения в базу данных.
	"""

	return {
		"_ver": version,
		"ID": user.id,
		"Username": user.username,
		"Name": user.full_name,
		"CreationDate": utils.get_timestamp()
	}

def get_default_global(version: int = utils.get_bot_version()) -> dict:
	"""
	Возвращает шаблон глобальной записи для сохранения в базу данных.
	"""

	return {
		"_ver": version
	}

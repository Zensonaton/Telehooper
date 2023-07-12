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

	assert not user.is_bot, "Попытка получить информацию из БД (метод get_user()) о боте."

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
			exists_ok=False,
			data=get_default_user(user)
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
			exists_ok=False,
			data=get_default_global()
		)
		await global_db.save()

		return global_db

def get_default_user(user: types.User, version: int = utils.get_bot_version()) -> dict:
	"""
	Возвращает шаблон пользователя для сохранения в базу данных.
	"""

	return {
		"DocVer": version,

		"ID": user.id, # ID пользователя.
		"Username": user.username, # Имя пользователя.
		"Name": user.full_name, # Полное имя пользователя.
		"CreationDate": utils.get_timestamp(), # Дата того, когда пользователь впервые написал боту.
		"BotBanned": False, # Заблокировал ли данный пользователь бота?
		"SettingsOverriden": {}, # Переопределённые настройки.
		"KnownLanguage": user.language_code, # Язык пользователя. Иногда может быть неизвестен.
		"Roles": [], # Роли пользователя.
		"Groups": [], # ID подключённых как диалоги/группы Telegram-групп.
		"Connections": { # Подключённые сервисы.
			# Данный объект пуст, он пополняется при подключении сервисов. См. метод get_default_subgroup().
		}
	}

def get_default_global(version: int = utils.get_bot_version()) -> dict:
	"""
	Возвращает шаблон глобальной записи для сохранения в базу данных.
	"""

	return {
		"DocVer": version
	}

async def get_group(chat: int | types.Chat) -> Document:
	"""
	Возвращает информацию о группе из базы данных. Учтите, что данный метод не создаёт группу, если она не была найдена.
	"""

	db = await get_db()

	return await db[f"group_{chat.id if isinstance(chat, types.Chat) else chat}"]

def get_default_group(chat: types.Chat, creator: types.User, status_message: types.Message, admin_rights: bool = False, topics_enabled: bool = False, version: int = utils.get_bot_version()) -> dict:
	"""
	Возвращает шаблон группы для сохранения в базу данных.
	"""

	return {
		"DocVer": version,

		"ID": chat.id, # ID группы.
		"Creator": creator.id, # ID создателя группы.
		"CreatedAt": utils.get_timestamp(), # Дата создания группы.
		"LastActivityAt": utils.get_timestamp(), # Дата последней активности в группе.
		"UserJoinedWarning": False, # Было ли предупреждение о том, что в группу добавили стороннего пользователя?
		"StatusMessageID": status_message.message_id, # ID (статусного) сообщения, которое было отправлено при добавлении бота в группу.
		"AdminRights": admin_rights, # Были ли боту выданы права администратора?
		"TopicsEnabled": topics_enabled, # Включены ли темы (топики) в группе?
		"Chats": { # Информация о подключённых чатах/группах в данной группе.

		},
		"Services": { # Информация о сервисах в данной группе.

		}
	}

def get_default_subgroup(topic_id: int, service_name: str, dialogue_id: int, dialogue_name: str, pinned_message: int) -> dict:
	"""
	Возвращает шаблон подгруппы (группы или топика группы) для сохранения в базу данных.
	"""

	return {
		"ID": topic_id, # ID топика. 0, если это не топик-группа.
		"Name": dialogue_name, # Название диалога/группы.
		"CreatedAt": utils.get_timestamp(), # Дата создания диалога/группы.
		"PinMessageID": pinned_message, # ID закреплённого сообщения.
		"Service": service_name, # Сервис, к которому подключён данный диалог/группа.
		"DialogueID": dialogue_id # ID диалога из сервиса.
	}

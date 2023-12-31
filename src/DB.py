# coding: utf-8

from typing import Literal
from aiocouch import CouchDB, Database, Document
from aiocouch.exception import NotFoundError
from aiogram.types import Chat, Message, User
from loguru import logger

import utils
from config import config


couchdb: CouchDB | None = None
DB: Database | None = None

async def get_db(db_name: str | None = None, check_auth: bool = False, force_new: bool = False) -> Database:
	"""
	Возвращает объект для работы с базой данных.

	:param db_name: Название базы данных. Если не указано, то будет использовано название из конфигурации.
	:param check_auth: Проверять ли авторизацию в базе данных?
	:param force_new: Создавать ли новую базу данных, если она не была найдена?
	"""

	global DB, couchdb


	if db_name is None:
		db_name = config.couchdb_name

	if couchdb is None:
		couchdb = CouchDB(
			config.couchdb_host,
			user=config.couchdb_user,
			password=config.couchdb_password.get_secret_value()
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

async def get_user(user: User, create_by_default: bool = True) -> Document:
	"""
	Возвращает данные пользователя из базы данных.

	:param user: Пользователь, информацию о котором нужно получить.
	:param create_by_default: Создавать ли пользователя, если он не был найден в базе данных?
	"""

	assert not user.is_bot, "Попытка получить информацию из БД (метод get_user()) о боте"

	db = await get_db()

	id = str(user.id)

	async def _get():
		try:
			return await db["user_" + id]
		except NotFoundError:
			if not create_by_default:
				raise NotFoundError(f"Пользователь с ID {id} не был найден в базе данных")

			# Пользователь не был найден, поэтому мы создаем его.
			user_db = await db.create(
				"user_" + id,
				exists_ok=False,
				data=get_default_user(user)
			)
			await user_db.save()

			return user_db

	user_db = await _get()
	if user_db["DocVer"] == utils.get_bot_version():
		return user_db

	while user_db["DocVer"] < utils.get_bot_version():
		ver = user_db["DocVer"]
		logger.debug(f"Делаю обновление пользователя {utils.get_telegram_logging_info(user)} с версии {ver} до версии {ver + 1}")

		if ver == 1:
			vk_connection = user_db["Connections"].get("VK")

			if vk_connection:
				for group in vk_connection["OwnedGroups"].values():
					group["URL"] = None

		user_db["DocVer"] += 1

	await user_db.save()
	return user_db

async def get_attachment_cache(service: str, create_by_default: bool = True) -> Document:
	"""
	Возвращает запись из БД, хранимую в себе кэш вложений определённого сервиса.

	:param service: Сервис, кэш вложений которого должен быть возвращён.
	:param create_by_default: Если равен `True`, то будет произведена запись если она не была найдена, в противном случае будет вызвана ошибка.
	"""

	db = await get_db()

	try:
		return await db[f"global_attchcache_{service}"]
	except NotFoundError:
		if not create_by_default:
			raise NotFoundError(f"Запись кэша вложений для сервиса {service} не была найдена в БД")

		# Запись кэша вложений не была найдена, поэтому создаём её.
		cache_db = await db.create(
			f"global_attchcache_{service}",
			exists_ok=False,
			data=get_default_attachment_cache(service)
		)
		await cache_db.save()

		return cache_db

def get_default_user(user: User, version: int = utils.get_bot_version()) -> dict:
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

def get_default_attachment_cache(service: str, version: int = utils.get_bot_version()) -> dict:
	"""
	Возвращает шаблон записи для кэша вложений сервиса.

	:param service: Сервис, для которого должен быть создан шаблон кэша вложений.
	"""

	return {
		"DocVer": version,
		"Service": service,
		"Attachments": {}
	}

async def get_group(chat: int | Chat) -> Document | None:
	"""
	Возвращает информацию о группе из базы данных. Учтите, что данный метод не создаёт группу, если она не была найдена.
	"""

	db = await get_db()

	async def _get():
		try:
			return await db[f"group_{chat.id if isinstance(chat, Chat) else chat}"]
		except NotFoundError:
			return None

	group_db = await _get()
	if group_db is None or group_db["DocVer"] == utils.get_bot_version():
		return group_db

	while group_db["DocVer"] < utils.get_bot_version():
		ver = group_db["DocVer"]
		logger.debug(f"Делаю обновление объекта группы {group_db.id} с версии {ver} до версии {ver + 1}")

		if ver == 2:
			group_db["Minibots"] = []
			group_db["AssociatedMinibots"] = {}

		group_db["DocVer"] += 1

	await group_db.save()
	return group_db

def get_default_group(chat: Chat, creator: User, status_message: Message, admin_rights: bool = False, topics_enabled: bool = False, version: int = utils.get_bot_version()) -> dict:
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
		"Minibots": [], # Список @username добавленных миниботов этой группы.
		"AssociatedMinibots": {}, # Ассоциированные @username миниботов и пользователей из сервиса.
		"Chats": { # Информация о подключённых чатах/группах в данной группе.

		},
		"Services": { # Информация о сервисах в данной группе.

		}
	}

def get_default_subgroup(topic_id: int, service_name: str, dialogue_id: int, dialogue_name: str, pinned_message: int, type: Literal["dialogue", "group", "newsfeed"]) -> dict:
	"""
	Возвращает шаблон подгруппы (группы или топика группы) для сохранения в базу данных.
	"""

	return {
		"ID": topic_id, # ID топика. 0, если это не топик-группа.
		"Name": dialogue_name, # Название диалога/группы.
		"CreatedAt": utils.get_timestamp(), # Дата создания диалога/группы.
		"PinMessageID": pinned_message, # ID закреплённого сообщения.
		"Service": service_name, # Сервис, к которому подключён данный диалог/группа.
		"DialogueID": dialogue_id, # ID диалога из сервиса.
		"Type": type # То, чем служит данная группа.
	}

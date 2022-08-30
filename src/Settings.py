# coding: utf-8

from typing import TYPE_CHECKING, Any, List, Optional, cast

from loguru import logger

import Utils
from DB import getDefaultCollection

if TYPE_CHECKING:
	from TelegramBot import TelehooperUser

REQUIRED_FILES_PROPERTIES = ["Name", "Default"]

class SettingsHandler:
	"""
	Интерфейс для работы с системой настроек.
	"""

	settingsTree: dict

	def __init__(self, settings_tree: dict) -> None:
		self.settingsTree = settings_tree

	def testIntegrity(self, raise_exception: bool = True, log_stats: bool = True):
		"""
		Проверяет древо настроек на наличие ошибок, а так же автоматически добавляет поля `ID`, `FullPath` и `IsAFile`
		"""

		try:
			self._test(self.settingsTree, "", log_stats)
		except Exception as error:
			if raise_exception:
				raise error

			return False

		return True

	def _test(self, object: dict, current_dir: str, log_stats: bool = True):
		"""
		Проверяет малую часть древа настроек на наличие ошибок.
		"""

		# TODO: Test DependsOn

		files = self.getFilesDict(object)
		for name, file in files.items():
			if not isinstance(file, dict):
				raise Exception(f"У файла \"{name}\" неправильный внутренний тип: {type(file)}, хотя должен быть dict.")

			for property in REQUIRED_FILES_PROPERTIES:
				if property in file:
					continue

				raise Exception(f"Важное значение \"{property}\" не было найдено в файле {name}.")

			file["ID"] = name
			file["FullPath"] = f"{current_dir}.{name}"
			file["IsAFile"] = True
			file["IsAFolder"] = False

		folders = self.getFoldersDict(object)
		for name, folder in folders.items():
			if not isinstance(folder, dict):
				raise Exception(f"У папки \"{name}\" неправильный внутренний тип: {type(folder)}, хотя должен быть dict.")

			folder["ID"] = name
			if current_dir:
				folder["FullPath"] = f"{current_dir}.{name}"
			else:
				folder["FullPath"] = name
			folder["IsAFile"] = False
			folder["IsAFolder"] = True


			self._test(folder, folder["FullPath"], False)

		if log_stats:
			logger.info(f"Сканирование древа настроек было завершено, ошибок не было обнаружено.")

	def listPath(self, path: str) -> List[str]:
		"""
		Парсит "путь" вида `a.b.c.d`, выдавая массив из "папок" и "файлов": `["a", "b", "c", "d"]` 
		"""

		return path.split(".")

	def getFolders(self, path: str) -> dict | None:
		"""
		Выдаёт `dict` со всеми "папками" по путю `path`.
		"""

		traversedRes = cast(dict, self.getByPath(path, default={}))

		return self.getFoldersDict(traversedRes)

	def getFiles(self, path: str) -> dict:
		"""
		Выдаёт `dict` со всеми "файлами" по путю `path`.
		"""

		traversedRes = cast(dict, self.getByPath(path, default={}))

		return self.getFilesDict(traversedRes)

	def getFoldersDict(self, object: dict) -> dict:
		"""
		Выдаёт `dict` со всеми "папками" из объекта `object`.
		"""

		return {k: v for k, v in object.items() if isinstance(v, dict) and "Default" not in v}

	def getFilesDict(self, object: dict) -> dict:
		"""
		Выдаёт `dict` со всеми "файлами" из объекта `object`.
		"""

		return {k: v for k, v in object.items() if isinstance(v, dict) and "Default" in v}

	def getByPath(self, path: str, default: Any = {}) -> dict | None:
		"""
		Возвращает dict со всеми папками и файлами по данному пути. Если ничего не будет найдено, то вернёт `default`.
		"""
		
		return Utils.traverseDict(self.settingsTree, *(self.listPath(path)), default=default)

	def renderByPath(self, path: List[str], user: Optional["TelehooperUser"] = None, put_settings_folder_first: bool = True, move_selected_to_end: bool = True, markdown_monospace_space_characters: bool = True, insert_user_path: bool = True) -> str:
		"""
		Возвращает строку с красиво оформленными файлами и папками по пути `path`. Идея была взята у команды `tree`.

		В коде данной функции используется древняя, страшная магия, смотреть не рекомендуется.
		"""

		# Сохраняем некоторые важные символы в переменные:
		boxChar_URD = " ├─ "
		boxChar_UR  = " └─ "

		# Строка, которая будет по итогу дополняться:
		outStr = ""

		# Добавляем "настройки" в самое начало:
		if put_settings_folder_first:
			outStr += "<b>📂 Настройки</b>"

			if insert_user_path:
				outStr += "  —  <code>/setting " + '.'.join(path) + "</code>" 

		outStr += "\n"

		def _addMarkdownFormat(string: str) -> str:
			"""
			Добавляет поля `<code> ... </code>`, если внешняя переменная `markdown_monospace_space_characters` равна `True`.
			"""

			if markdown_monospace_space_characters:
				return "<code>" + string + "</code>"

			return string

		def _render(object: dict, pathIndex: int, fullPath: list[str]) -> str:
			"""
			Выполняет рендер специфичных частей.
			"""

			# Строка, которая будет по итогу дополняться:
			outStr = ""

			# Проходимся по всем папкам:
			folders = self.getFoldersDict(object)

			# Если это нужно, то открытую папку переносим в самый конец:
			if move_selected_to_end and len(fullPath) and pathIndex < len(fullPath) and fullPath[pathIndex] in folders:
				folders[fullPath[pathIndex]] = folders.pop(fullPath[pathIndex])

			# Проходимся по папкам.
			foldersLen = len(folders)
			for index, folder in enumerate(folders, start=1):
				folderName = folder
				folder = folders[folder]
				friendlyName = folder["Name"]
				isAvailable = True
				folderCharacter = "📁 "

				if user:
					isAvailable = self.checkSettingAvailability(user, folder["FullPath"])

				if pathIndex < len(fullPath) and fullPath[pathIndex] == folderName:
					friendlyName = "<b>" + friendlyName + "</b>"
					folderCharacter = "📂 "

				outStr += _addMarkdownFormat(("    " * pathIndex) + (boxChar_URD if (index) < foldersLen else boxChar_UR)) + ("" if isAvailable else "<s>") + folderCharacter + friendlyName + ("" if isAvailable else "</s>") + "\n"

			
			# Проходимся по всем файлам:
			files = self.getFilesDict(object)

			# Если это нужно, то открытый файл переносим в самый конец:
			if move_selected_to_end and len(fullPath) and pathIndex < len(fullPath) and fullPath[pathIndex] in files:
				files[fullPath[pathIndex]] = files.pop(fullPath[pathIndex])

			filesLen = len(files)
			for index, file in enumerate(files, start=1):
				fileName = file
				file = files[file]
				isAvailable = True
				friendlyName = file["Name"]

				if user:
					isAvailable = self.checkSettingAvailability(user, file["FullPath"])

				if pathIndex < len(fullPath) and fullPath[pathIndex] == fileName:
					friendlyName = "<b>" + friendlyName + "</b> ⬅️"


				outStr += _addMarkdownFormat(("    " * pathIndex) + (boxChar_URD if (index) < filesLen else boxChar_UR)) + ("" if isAvailable else "<s>") + "⚙️ " + friendlyName + ("" if isAvailable else "</s>") + "\n"


			# Если у наш путь ещё не закончился, рекурсивно продолжаем:
			if pathIndex < len(fullPath):
				outStr += _render(object[fullPath[pathIndex]], pathIndex + 1, fullPath)


			return outStr

		outStr += _render(self.settingsTree, 0, path)

		# Удаляем лишний /n, если таковой имеется:
		if outStr.endswith("\n"):
			outStr = outStr[:-1]


		return outStr

	def getDefaultSetting(self, path: str) -> Any | None:
		"""
		Выдаёт значение по умолчанию у настройки, либо `None`.
		"""

		return cast(dict, self.getByPath(path, default={})).get("Default", None)

	def getUserSetting(self, user: "TelehooperUser", path: str) -> Any | None:
		"""
		Достаёт настройку у пользователя, или же `None`, если такой настройки нет.
		"""

		DB = getDefaultCollection()

		res = DB.find_one({"_id": user.TGUser.id})

		if not res:
			return None

		if not self.getByPath(path):
			raise Exception(f"Настройка \"{path}\" не существует")

		userSetting = res["Settings"].get(path.replace(".", "_"), None)

		if userSetting:
			return userSetting

		return self.getDefaultSetting(path)

	def setUserSetting(self, user: "TelehooperUser", path: str, new_value: Any):
		"""
		Сохраняет настройку в ДБ.
		"""

		DB = getDefaultCollection()

		res = DB.find_one({"_id": user.TGUser.id})

		if not res:
			return

		if not self.getByPath(path):
			raise Exception(f"Настройка \"{path}\" не существует")

		path = path.replace(".", "_")

		userSetting = res["Settings"].get(path, None)

		if new_value == userSetting:
			# В базе данных бот будет хранить только изменённые настройки.

			return

		DB.update_one(
			{
				"_id": user.TGUser.id
			},
			
			{
				"$set": {
					f"Settings.{path}": new_value
				}
			},
			
			upsert=True
		)

	def checkSettingAvailability(self, user: "TelehooperUser", path: str) -> bool:
		"""
		Проверяет условия `DependsOn` у настройки. Если таковая настройка не была найдена, возвращает ошибку.
		"""

		settingSelected = cast(dict, self.getByPath(path))
		
		# Проходимся по всем условиям, если таковые имеются:
		for index, condition in enumerate(settingSelected.get("DependsOn", [])):
			if "EqualTo" in condition and self.getUserSetting(user, condition["LookIn"]) != condition["EqualTo"]:
				return False

		return True

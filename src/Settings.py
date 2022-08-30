# coding: utf-8

from typing import TYPE_CHECKING, Any, List, cast
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

		stat_files = 0
		stat_folders = 0

		# TODO: Test DependsOn

		files = Utils.getDictValuesByKeyPrefixes(object, "_")
		for name, file in files.items():
			stat_files += 1

			if not isinstance(file, dict):
				raise Exception(f"У файла \"{name}\" неправильный внутренний тип: {type(file)}, хотя должен быть dict.")

			for property in REQUIRED_FILES_PROPERTIES:
				if property in file:
					continue

				raise Exception(f"Важное значение \"{property}\" не было найдено в файле {name}.")

			file["ID"] = name
			file["FullPath"] = f"{current_dir}.{name}"
			file["IsAFile"] = True

		folders = Utils.getDictValuesByKeyPrefixes(object, "?")
		for name, folder in folders.items():
			stat_folders += 1

			if not isinstance(folder, dict):
				raise Exception(f"У папки \"{name}\" неправильный внутренний тип: {type(folder)}, хотя должен быть dict.")

			folder["ID"] = name
			if current_dir:
				folder["FullPath"] = f"{current_dir}.{name}"
			else:
				folder["FullPath"] = name
			folder["IsAFile"] = False


			self._test(folder, folder["FullPath"], False)

		if log_stats:
			logger.info(f"Сканирование древа настроек было завершено, было просканировано {stat_files} файлов и {stat_folders} папок.")

	def listPath(self, path: str) -> List[str]:
		"""
		Парсит "путь" вида `a.b.c.d`, выдавая массив из "папок" и "файлов": `["a", "b", "c", "d"]` 
		"""

		return path.split(".")

	def resolveListPath(self, path: List[str]) -> List[str] | None:
		"""
		Парсит "путь" вида `["a", "b", "c", "d"]`, выдавая путь с префиксами: `["?a", "?b", "?c", "_d"]`. Если функция не находит какую-то часть пути, то результатом оказывается `None`.
		"""

		curObject = self.settingsTree
		resPath = []
		for index, element in enumerate(path):
			if   ("?" + element) in curObject:
				element = ("?" + element)

				curObject = curObject[element]
				resPath.append(element)

				continue
			elif ("_" + element) in curObject:
				element = ("_" + element)

				curObject = curObject[element]
				resPath.append(element)

				continue
			else:
				# Ничего не нашли, выходим:

				return None

		return resPath

	def getFolders(self, path: str, default: Any = {}) -> dict | None:
		"""
		Выдаёт `dict` со всеми "папками" по путю `path`. У всех папок в переменной `SETTINGS` префикс - `?`.
		"""

		return Utils.getDictValuesByKeyPrefixes(
			Utils.traverseDict(self.settingsTree, *(self.listPath(path)), default=default), 
			"?"
		)

	def getFiles(self, path: str, default: Any = {}) -> dict:
		"""
		Выдаёт `dict` со всеми "файлами" по путю `path`. У всех файлов в переменной `SETTINGS` префикс - `_`.
		"""

		return Utils.getDictValuesByKeyPrefixes(
			Utils.traverseDict(self.settingsTree, *(self.listPath(path)), default=default), 
			"_"
		)

	def getByPath(self, path: str, default: Any = {}) -> dict | None:
		"""
		Возвращает dict со всеми папками и файлами по данному пути. Если ничего не будет найдено, то вернёт `default`.
		"""
		
		return Utils.traverseDict(self.settingsTree, *(self.listPath(path)), default=default)

	def renderByPath(self, path: List[str], put_settings_folder_first: bool = True, move_selected_to_end: bool = True, markdown_monospace_space_characters: bool = True, insert_user_path: bool = True) -> str:
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
				outStr += "  —  <code>/setting " + '.'.join(self.convertResolvedPathToUserFriendly(path)) + "</code>" 

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
			folders = Utils.getDictValuesByKeyPrefixes(object, "?")

			# Если это нужно, то открытую папку переносим в самый конец:
			if move_selected_to_end and len(fullPath) and pathIndex < len(fullPath) and fullPath[pathIndex] in folders:
				folders[fullPath[pathIndex]] = folders.pop(fullPath[pathIndex])

			# Проходимся по папкам.
			foldersLen = len(folders)
			for index, folder in enumerate(folders):
				folderName = folder
				folder = folders[folder]
				friendlyName = folder["Name"]
				isAvailable = True
				folderCharacter = "📁 "

				if pathIndex < len(fullPath) and fullPath[pathIndex] == folderName:
					friendlyName = "<b>" + friendlyName + "</b>"
					folderCharacter = "📂 "

				outStr += _addMarkdownFormat(("    " * pathIndex) + (boxChar_URD if (index + 1) < foldersLen else boxChar_UR)) + ("" if isAvailable else "<s>") + folderCharacter + friendlyName + ("" if isAvailable else "</s>") + "\n"

			
			# Проходимся по всем файлам:
			files = Utils.getDictValuesByKeyPrefixes(object, "_")

			# Если это нужно, то открытый файл переносим в самый конец:
			if move_selected_to_end and len(fullPath) and pathIndex < len(fullPath) and fullPath[pathIndex] in files:
				files[fullPath[pathIndex]] = files.pop(fullPath[pathIndex])

			filesLen = len(files)
			for index, file in enumerate(files):
				fileName = file
				file = files[file]
				isAvailable = True
				friendlyName = file["Name"]

				if pathIndex < len(fullPath) and fullPath[pathIndex] == fileName:
					friendlyName = "<b>" + friendlyName + "</b> ⬅️"


				outStr += _addMarkdownFormat(("    " * pathIndex) + (boxChar_URD if (index + 1) < filesLen else boxChar_UR)) + ("" if isAvailable else "<s>") + "⚙️ " + friendlyName + ("" if isAvailable else "</s>") + "\n"


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


		if not path.startswith("?"):
			res = self.resolveListPath(self.listPath(path))

			if not res:
				return None

			path = ".".join(res)

		res = self.getByPath(path, default={})

		return cast(dict, res).get("Default", None)

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

		path = path.replace(".", "_")

		DB = getDefaultCollection()

		res = DB.find_one({"_id": user.TGUser.id})

		if not res:
			return

		if not self.getByPath(path):
			raise Exception(f"Настройка \"{path}\" не существует")

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

	def convertResolvedPathToUserFriendly(self, resolved_path: List[str]) -> List[str]:
		"""
		Превращает лист вида `["?a", "?b", "c?", "_d"]` в лист вида `["a", "b", "c", "d"]`
		"""

		return [i[1:] for i in resolved_path]

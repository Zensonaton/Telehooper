# coding: utf-8

from typing import Any, cast
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from case_insensitive_dict import CaseInsensitiveDict
from loguru import logger


SETTING_EMOJI = "⚙️"
OPEN_FOLDER_EMOJI = "📂"
CLOSED_FOLDER_EMOJI = "📁"
BOX_CHAR_CONNECTED = " ├─ "
BOX_CHAR_CLOSING  = " └─ "

SETTINGS_TREE = {
	"Visual": {
		"Name": "Визуальные настройки",

		"UsePinInDialogues": {
			"Name": "Закреп со статусом",
			"Documentation": (
				"Указывает, может ли Telehooper создавать закреплённое сообщение в новых диалогах Telegram, в которых может отображаться полезная информация:\n"
				"  • состояние «онлайн»,\n"
				"  • имя пользователя,\n"
				"  • статус «прочитано» у последнего отправленного сообщения.\n"
				"\n"
				"Так же рекомендуется посмотреть настройку <i>⚙️ Смещение слов в закрепе</i> (<code>/s Visual.PinCharDistance</code>) для настройки расстояния между словами в этом закреплённом сообщении."
			),
			"Default": True
		},
		"PinOrderReversed": {
			"Name": "Порядок слов в закрепе",
			"Documentation": (
                "При включённой опции <i>⚙️ Закреп со статусом</i> (<code>/s Visual.UsePinInDialogues</code>), указывает, нужно ли боту поменять порядок поля статуса «онлайн» и поля «прочитано» в закреплённом сообщении.\n"
				"\n"
				"Увидеть как это выглядит можно в следующем сообщении, которое будет автоматически закреплено."
			),
			"Default": False,
			"DependsOn": [{
				"LookIn": "Visual.UsePinInDialogues",
				"EqualTo": True
			}]
		},
		"PinCharDistance": {
			"Name": "Расстояние слов в закрепе",
			"Documentation": (
                "При включённой опции <i>⚙️ Закреп со статусом</i> (<code>/s Visual.UsePinInDialogues</code>), указывает расстояние между словами, указывающих состояние «онлайн», имя пользователя, и статус «прочитано» последнего отправленного сообщения.\n"
				"\n"
				"Данная опция может быть нужна, если закреплённое сообщение отображается на вашем экране некорректно.\n"
				"\n"
				"Увидеть как это выглядит можно в следующем сообщении, которое будет автоматически закреплено."
			),
			"ButtonType": "range",
			"Default": 5,
			"Min": 1,
			"Max": 20,
			"DependsOn": [{
				"LookIn": "Visual.UsePinInDialogues",
				"EqualTo": True
			}]
		}
	},

	"Security": {
		"Name": "Безопасность",

		"StoreTokens": {
			"Name": "Хранение токенов в БД",
			"Documentation": (
                "Указывается, может ли Telehooper хранить токены авторизации <a href=\"https://dev.vk.com/api/access-token/getting-started\">[Документация ВК]</a> в его базе данных для автоматического процесса восстановления сессий сервисов после перезагрузок.\n"
				"\n"
				"Выключив эту опцию, <b>Вы повысите безопасность подключённых сервисов</b> в случае взлома базы данных бота, однако, после своей перезагрузки Telehooper не сумеет переподключиться <b>ко всем сервисам</b>, что были подключены ранее, и поэтому Вам придётся снова производить процедуру авторизации.\n"
				"Изменение данной настройки не поменяет состояние уже подключённых сервисов."
			),
			"Default": True
		},
		"MediaCache": {
			"Name": "Кэш медиа",
			"Documentation": (
                "Определяет, может ли Telehooper хранить ID отправленных и/ли полученных медиа с типами, описанными ниже, с целью кэширования, уменьшения нагрузки и ускорения работы бота.\n"
				"Кэшируемые типы медиа:\n"
				"  • Стикеры,\n"
				"  • GIF-изображения.\n"
                "\n"
				"О безопасности: Даже при взломе базы данных бота получить доступ к медиа невозможно. При получении нового медиа, например, стикера, бот отправляет медиа как сообщение в Telegram, после чего у бота появляется несколько технических полей: <code>FileID</code> (Telegram) и <code>attachment</code> (ВКонтакте). Бот сохраняет в БД SHA-256 хэш FileID как ключ, и использует зашифрованный attachment, используя FileID как ключ шифрования."
			),
			"Default": True
		}
	},

	"Services": {
		"Name": "Настройки сервисов",

		"MarkAsReadButton": {
			"Name": "Кнопка «прочитать»",
			"Documentation": (
                "Включает или отключает кнопку «Прочитать» возле новых сообщений, отправленных собеседником диалога. Данная кнопка показана под самым «последним» отправленным собеседником сообщением, и она автоматически скрывается при нажатии. Данная кнопка выполняет такое же действие, как и команда <code>/read</code>, если используемый сервис это поддерживает.\n"
				"\n"
				"Так же рекомендуется уделить внимание на настройку <i>⚙️ Закреп со статусом</i> (<code>/s Visual.UsePinInDialogues</code>), ведь в закреплённом сообщении показана информации о том, было прочитано сообщение или нет."
			),
			"Default": True
		},
		"WaitToType": {
			"Name": "Задержка для «печати»",
			"Documentation": (
                "Включает специальную задержку в 500 миллисекунд перед отправкой сообщения в сервисы. Перед отправкой сообщения, в сервисе сообщение сразу отмечается как «прочитанное», и начинается анимация «пользователь печатает».\n"
				"\n"
				"Отключая данную настройку, Ваше сообщение будет отправляться мгновенно, однако анимации «пользователь печатает» не будет."
			),
			"Default": False
		},
		"SetOnline": {
			"Name": "Статус «онлайн»",
			"Documentation": (
				"Включив эту настройку, Вы позволите Telehooper устанавливать статус «онлайн» в поддерживаемых сервисах после отправки любого сообщения через бота.\n"
				"\n"
				"Боты в Telegram не имеют доступа к статусу «онлайн» их пользователей, поэтому Вы можете быть «невидимыми», если эта настройка выключена."
			),
			"Default": True
		},
		"ViaServiceMessages": {
			"Name": "Показ Ваших сообщений",
			"Documentation": (
				"Указывает, может ли Telehooper пересылать отправленные Вами сообщения, которые были отправлены внутри сервиса, используя при этом префикс «Вы»."
			),
			"Default": True
		}
	}
}

class SettingsHandler:
	"""
	Класс-помощник для работы с настройками.
	"""

	settings: dict

	def __init__(self, settings: dict) -> None:
		self.settings = settings

		self.integrity_check()
		self.fill_tree_fields()

	def integrity_check(self) -> None:
		"""
		Проверяет целостность настроек в древе.
		"""

		SETTINGS_KEYS = {
			"Name": str,
			"Documentation": str,
			"Default": None
		}

		def _check(check: dict) -> None:
			# TODO: Проверка поля DependsOn.

			for name, value in check.items():
				if type(value) != dict:
					continue

				is_value = "Documentation" in value

				if is_value:
					for name, key_type in SETTINGS_KEYS.items():
						if name not in value:
							raise ValueError(f"Настройка {name} не содержит свойство {name}.")

						if key_type and type(value[name]) != key_type:
							raise ValueError(f"Значение настройки {name} не является {key_type}.")
				else:
					_check(value)

		_check(self.settings)

	def fill_tree_fields(self) -> None:
		"""
		Добавляет следующие поля в древо настроек для более простой работы с ними.

		Root-объект:
		 1. `Paths` — лист всех существующих настроек в древе.

		Все объекты:
		 1. `IsValue` — является ли настройка значением (True) или папкой (False),
		 2. `IsFolder` — является ли настройка папкой (True) или значением (False),
		 3. `ParentPath` — путь к родительской папке,
		 4. `Path` — полный путь к настройке.
		 5. `PathSplitted` — список путей к настройке, разделённый по точкам.

		Настройки (`IsValue`):
		 1. `DependsOn` — список зависимостей настройки. (если не существовал)
		 2. `ButtonType` — тип кнопок для изменения этой настройки. (если не существовал; тип определяется из поля `Default`)
		"""

		known_paths = []
		def _fill_fields(setting: dict, path: str = "") -> None:
			items = setting.copy().items()

			for key, value in items:
				if type(value) != dict:
					continue

				is_value = "Documentation" in value
				is_folder = not is_value
				new_path = f"{path}.{key}" if path else key

				logger.debug(f"Обрабатываю {'папку' if is_folder else 'настройку'} {new_path}.")

				value["IsValue"] = is_value
				value["IsFolder"] = is_folder
				value["ParentPath"] = path
				value["Path"] = new_path
				value["PathSplitted"] = new_path.split(".")

				if is_value:
					if "DependsOn" not in value:
						value["DependsOn"] = []

					if "ButtonType" not in value:
						if type(value["Default"]) != bool:
							raise ValueError(f"Не удалось определить тип кнопок (ButtonType) для настройки {new_path}. Значение Default={value['Default']}.")

						value["ButtonType"] = "bool"

				known_paths.append(new_path)

				_fill_fields(value, new_path)

		# Заполняем все поля.
		_fill_fields(self.settings)

		# Сохраняем список всех путей.
		self.settings["Paths"] = known_paths

	def get_buttons_by_setting_type(self, setting: dict, current_value) -> list[InlineKeyboardButton]:
		"""
		Возвращает кнопки клавиатуры в зависимости от типа настройки.
		"""

		return_list = []
		buttons = {}

		if setting["ButtonType"] == "bool":
			current_value = cast(bool, current_value)

			buttons = {
				f"✔️ Включить": True,
				f"✖️ Выключить": False
			}
		elif setting["ButtonType"] == "range":
			current_value = cast(int, current_value)
			step = setting.get("Step", 1)

			buttons = {
				"⏪": setting["Min"],
				"◀️": None if current_value - step < setting["Min"] else current_value - step,
				str(current_value): None,
				"▶️": None if current_value + step > setting["Max"] else current_value + step,
				"⏩": setting["Max"]
			}
		else:
			raise ValueError(f"Неизвестный тип кнопок для настройки {setting['Path']}.")

		for text, value in buttons.items():
			callback_data = value
			is_equal = value == current_value

			if is_equal:
				callback_data = None

			return_list.append(
				InlineKeyboardButton(
					text=text.upper() if is_equal else text,
					callback_data="do-nothing" if callback_data == None else f"/settings set {setting['Path']} {callback_data}"
				)
			)

		return return_list

	def get_keyboard(self, path: str | None = None, user_settings: dict | None = None) -> InlineKeyboardMarkup:
		"""
		Возвращает клавиатуру для древа настроек, по заданному пути `path` (если указан).
		"""

		keyboard_buttons = []

		if path is None:
			path = ""

		if user_settings is None:
			user_settings = {}

		path_splitted = path.split(".")
		if path_splitted[-1] == "":
			path_splitted = path_splitted[:-1]

		parent = ".".join(path_splitted[:-1])
		level = len(path_splitted)

		setting = self.settings
		settings_caseins = CaseInsensitiveDict(setting)

		for part in path_splitted:
			if not part:
				break

			lower_part = part.lower()

			if lower_part not in settings_caseins:
				break

			setting = settings_caseins[part]
			settings_caseins = CaseInsensitiveDict(setting)

		if setting.get("IsValue"):
			keyboard_buttons.append(
				self.get_buttons_by_setting_type(setting, user_settings.get(path, setting["Default"]))
			)
		else:
			for value in setting.values():
				if not isinstance(value, dict):
					continue

				if not "Name" in value:
					continue

				keyboard_buttons.append([
					InlineKeyboardButton(
						text=f"{CLOSED_FOLDER_EMOJI if value['IsFolder'] else SETTING_EMOJI} {value['Name']}",
						callback_data=f"/settings {value['Path']}"
					)
				])

		upper_keyboard = [InlineKeyboardButton(text="ㅤ", callback_data="do-nothing")]

		if level >= 1:
			upper_keyboard = [InlineKeyboardButton(text="🔙 Назад", callback_data=f"/settings {parent}")]

		if level >= 2:
			upper_keyboard.append(InlineKeyboardButton(text="🔝 В начало", callback_data="/settings"))

		return InlineKeyboardMarkup(
			inline_keyboard=[
				upper_keyboard,

				*keyboard_buttons
			]
		)

	def render_tree(self, path: str | None = None) -> str:
		"""
		Отрисовывает дерево настроек, выглядящее как команда `tree` в Windows.
		"""

		def _render(path: list[str], level: int, settings_dict: dict) -> str:
			working_str = ""
			late_append_str = ""

			real_settings_dict = [value for key, value in settings_dict.items() if isinstance(value, dict) and "Name" in value]

			# Перемещаем "выбранный" вариант в конец списка.
			for index, setting in enumerate(real_settings_dict):
				if level < len(path) and level < len(setting["PathSplitted"]) and path[level].lower() == setting["PathSplitted"][level].lower():
					real_settings_dict.append(real_settings_dict.pop(index))

					break

			# Проходимся по всем вариантам.
			for index, setting in enumerate(real_settings_dict):
				is_selected = level < len(path) and level < len(setting["PathSplitted"]) and path[level].lower() == setting["PathSplitted"][level].lower()
				is_folder = setting["IsFolder"]
				is_last = index == len(real_settings_dict) - 1

				if is_folder:
					leaf_str = f"<code>{' ' * (level * 3)}{BOX_CHAR_CLOSING if is_last else BOX_CHAR_CONNECTED}{OPEN_FOLDER_EMOJI if is_selected else CLOSED_FOLDER_EMOJI}</code> {'<b>' if is_selected else ''}{setting['Name']}{'</b>:' if is_selected else ''}\n"
				else:
					leaf_str = f"<code>{' ' * (level * 3)}{BOX_CHAR_CLOSING if is_last else BOX_CHAR_CONNECTED}{SETTING_EMOJI}</code> {'<b>' if is_selected else ''}{setting['Name']}{'</b> ◀️' if is_selected else ''}\n"

				if is_selected:
					late_append_str += leaf_str + _render(path, level + 1, setting)
				else:
					working_str += leaf_str

			working_str += late_append_str

			return working_str

		if path is None:
			path = ""

		return _render(path.split("."), 0, self.settings)

	def get_setting(self, path: str) -> dict:
		"""
		Получает значение настройки по пути. Может вернуть как саму настройку, так и "папку" с настройками, в зависимости от `path`.

		Если настройка не существует то вызывается исключение `KeyError`.
		"""

		path_splitted = path.split(".")

		setting = self.settings.copy()
		for part in path_splitted:
			setting = setting[part]

		return setting

	def get_default_setting_value(self, path: str) -> Any:
		"""
		Возвращает значение по умолчанию для настройки по пути `path`.

		Если настройка не существует то вызывается исключение `KeyError`.
		"""

		return self.get_setting(path)["Default"]

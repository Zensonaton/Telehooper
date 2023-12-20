# coding: utf-8

import re
from typing import Any, cast

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from case_insensitive_dict import CaseInsensitiveDict
from loguru import logger

import utils
from config import config


SETTING_EMOJI = "⚙️"
OPEN_FOLDER_EMOJI = "📂"
CLOSED_FOLDER_EMOJI = "📁"
BOX_CHAR_CONNECTED = " ├─ "
BOX_CHAR_CLOSING  = " └─ "

SETTINGS_TREE = {
	"Visual": {
		"Name": "Визуальные настройки"
	},

	"Security": {
		"Name": "Безопасность",

		"StoreTokens": {
			"Name": "Хранение токенов в БД",
			"Documentation": (
                "Указывается, может ли Telehooper хранить токены авторизации <a href=\"https://dev.vk.com/api/access-token/getting-started\">[Документация ВК]</a> в его базе данных для автоматического процесса восстановления сессий сервисов после перезагрузок.\n"
				"\n"
				"Выключив эту опцию, <b>Вы повысите безопасность подключённых сервисов</b> в случае взлома базы данных бота, однако, после своей перезагрузки Telehooper не сумеет переподключиться ко всем сервисам, что были подключены ранее, и поэтому Вам придётся снова производить процедуру авторизации.\n"
				"Изменение данной настройки не поменяет состояние уже подключённых сервисов."
			),
			"ButtonType": "bool",
			"Default": True
		},
		"MediaCache": {
			"Name": "Кэш медиа",
			"Documentation": (
                "Определяет, может ли Telehooper хранить ID отправленных и/ли полученных медиа с типами, описанными ниже, с целью кэширования, уменьшения нагрузки и ускорения работы бота.\n"
				"Кэшируемые типы медиа:\n"
				" • Стикеры,\n"
				" • GIF-изображения.\n"
                "\n"
				"О безопасности: Даже при взломе базы данных бота получить доступ к медиа невозможно. При получении нового медиа, например, стикера, бот отправляет медиа как сообщение в Telegram, после чего у бота появляется несколько технических полей: <code>FileID</code> (Telegram) и <code>attachment</code> (ВКонтакте). Бот сохраняет в БД SHA-256 хэш FileID как ключ, и использует зашифрованный attachment, используя FileID как ключ шифрования."
			),
			"ButtonType": "bool",
			"Default": True
		},
		"GetChatURL": {
			"Name": "Создание ссылки на чат",
			"Documentation": (
				"Указывает, может ли Telehooper создавать ссылки на приглашения в группу после подключения бота к сервису. Это нужно для того, что бы в команде /me Вы могли запросто перейти в группу Telegram просто нажав на ссылку.\n"
				"\n"
				"Ссылка на вступление шифруется специальным ключём, а так же при попытке перейти по ней Telegram запросит разрешение на вход от администраторов группы, т.е., Вас.\n"
				"\n"
				"Даже если данная настройка выключена, Telehooper будет пытаться получать ссылку на чат альтернативными методами, однако они работают не всегда."
			),
			"ButtonType": "bool",
			"Default": True
		}
	},

	"Services": {
		"Name": "Настройки сервисов",

		"VK": {
			"Name": "ВКонтакте",

			"SetOnline": {
				"Name": "Статус «онлайн»",
				"Documentation": (
					"Включив эту настройку, Вы позволите Telehooper устанавливать статус «онлайн» после отправки сообщения через бота.\n"
					"\n"
					"Боты в Telegram не имеют доступа к статусу «онлайн» их пользователей, поэтому Вы можете быть «невидимыми», если эта настройка выключена."
				),
				"ButtonType": "bool",
				"Default": True
			},
			"ViaServiceMessages": {
				"Name": "Показ Ваших сообщений",
				"Documentation": (
					"Включив эту настройку, Telehooper будет пересылать отправленные Вами сообщения, которые Вы отправили не через бота, а через сам сервис.\n"
					"\n"
					"Сообщения, отправляемые при этой настройке имеют следующий вид:\n"
					"  [<b>Вы</b>]: текст Вашего сообщения.\n"
					"\n"
					"Такие сообщения отправляются без уведомлений."
				),
				"ButtonType": "bool",
				"Default": True
			},
			"HDVideo": {
				"Name": "HD видео",
				"Documentation": (
					"Включив эту настройку, Вы разрешите Telehooper при загрузке видео с сервисов использовать разрешение HD (1080p) при скачивании.\n"
					"\n"
					"Учтите, что бот отправит только то видео, размер которого не превышает 50 МБ.\n"
					"Помимо этого, учтите, что включение данной настройки может значительно увеличить задержку между отправкой видео."
				),
				"ButtonType": "bool",
				"Default": False
			},
			"CleanupAfterUse": {
				"Name": "Удаление команды после выполнения",
				"Documentation": (
					"Указывает, стоит ли боту «подчищать» сообщения с командами <code>/read</code>, <code>/delete</code> после их выполнения."
				),
				"ButtonType": "bool",
				"Default": True
			},
			"MobileVKURLs": {
				"Name": "Использовать m.vk.com",
				"Documentation": (
					"Telehooper, в некоторых местах, использует ссылки на ВКонтакте. К примеру, бот может приложить ссылку к сообщению, если в нём есть один из следующих типов вложений:\n"
					" • Подарок,\n"
					" • Репост,\n"
					" • Опрос,\n"
					" • <i>...и многие другие</i>.\n"
					"\n"
					"Если Вы включите данную настройку, то Telehooper будет использовать ссылку на мобильную версию ВКонтакте (<code>m.vk.com</code>), в ином случае будет использовать полную версию сайта (<code>vk.com</code>).\n"
					"Мобильная версия ВКонтакте намного «легче»: Страницы мобильной версии намного быстрее загружаются и требуют меньшего количества ресурсов."
				),
				"ButtonType": "bool",
				"Default": True
			},
			"FWDAsReply": {
				"Name": "Единичное «пересланное» как ответ",
				"Documentation": (
					"Во ВКонтакте, делать «ответы» на сообщения можно двумя способами:\n"
					" • Переслать сообщение в тот же диалог,\n"
					" • Нажать на кнопку «Ответить».\n"
					"\n"
					"Именно для первого случая и сделана эта настройка; Если данная настройка включена, то в случае, если Ваш собеседник переслал лишь одно сообщение, то тогда Telehooper будет отображать сообщение не как «пересланное», а как «ответ»."
				),
				"ButtonType": "bool",
				"Default": True
			},
			"CompactNames": {
				"Name": "Компактные имена",
				"Documentation": (
					"Telehooper при работе в беседах использует следующий префикс сообщений:\n"
					"[<b>Имя Фамилия</b>]: Текст сообщения.\n"
					"\n"
					"Однако, не всегда есть необходимость в полном отображении фамилии человека, поэтому Вы можете включить данную настройку, после чего Telehooper будет использовать более компактный префикс сообщений:\n"
					"[<b>Имя Ф.</b>]: Текст сообщения."
				),
				"ButtonType": "bool",
				"Default": True
			},
			"SyncGroupInfo": {
				"Name": "Синхронизация параметров диалога",
				"Documentation": (
					"Если данная настройка включена, то Telehooper будет копировать следующие свойства диалога, что бы быть группа Telegram была похожей на диалог ВКонтакте:\n"
					" • Имя диалога,\n"
					" • Фотография диалога,\n"
					" • Описание диалога,\n"
					" • <i>... и, возможно, другие.</i>"
				),
				"ButtonType": "bool",
				"Default": True
			},
			"OtherUsrMsgFwd": {
				"Name": "Обработка чужих сообщений группы",
				"Documentation": (
					"Так как каждый «диалог» сервиса работает как отдельная «группы» в Telegram, Вы можете добавлять сторонних пользователей из Telegram в свою группу.\n"
					"\n"
					"Данная настройка диктует то, как Telehooper будет работать в случаях, если Вы добавили в группу-диалог стороннего Telegram-пользователя.\n"
					"\n"
					"Значение «не пересылать»:\n"
					" • Telehooper не будет пересылать сообщения от «чужого» пользователя, который был добавлен в группу.\n"
					"\n"
					"Значение «от имени владельца группы»:\n"
					" • Telehooper будет пересылать любые сообщения отправленные в группе (в том числе и от «чужих» пользователей) от имени Вашей страницы. Не рекомендуется включать.\n"
					"\n"
					"Значение «от имени отправившего»:\n"
					" • Telehooper будет пересылать сообщение от имени того человека, который и отправил сообщение. Данная настройка работает только в том случае, если у пользователя, который отправил сообщение, есть подключение к сервису, в ином случае сообщение будет тихо проигнорировано."
				),
				"ButtonType": "enum",
				"Default": "as-self",
				"EnumValues": {
					"ignore": "Не пересылать",
					"as-owner": "От имени владельца группы",
					"as-self": "От имени отправившего"
				},
				"VerticalButtons": True
			},
			"AutoRead": {
				"Name": "Авто прочитывание сообщений",
				"Documentation": (
					"Ввиду ограничений Telegram, Telehooper не знает, когда Вы читаете сообщения, заходя в связанный со ВКонтакте группой. Единственный вариант, как можно пометить сообщение как прочитанное - использовать команду <code>/read</code>.\n"
					"\n"
					"Вы можете автоматически помечать сообщения как «прочитанные» после их отправки Вашим собеседников, делая список диалогов ВКонтакте более «чистым».\n"
					"Указать время, после которого сообщение помечается как «прочитанное» можно при помощи настройки {{Services.VK.AutoReadTime}}.\n"
					"\n"
					"Значение «не прочитывать»:\n"
					" • Telehooper не будет автоматически помечать сообщения как «прочитанные».\n"
					"\n"
					"Значение «обычные чаты»:\n"
					" • Telehooper будет автоматически «прочитывать» сообщения во всех чатах, которые связаны с Telehooper.\n"
					"\n"
					"Значение «только беседы»:\n"
					" • Telehooper будет автоматически «прочитывать» сообщения только в беседах, которые связаны с Telehooper.\n"
					"\n"
					"Значение «все чаты»:\n"
					" • Telehooper будет автоматически «прочитывать» сообщения во всех чатах, которые связаны с Telehooper."
				),
				"ButtonType": "enum",
				"Default": "ignore",
				"EnumValues": {
					"ignore": "Не прочитывать",
					"single": "Обычные чаты",
					"multiuser": "Только беседы",
					"all": "Все чаты"
				},
				"VerticalButtons": True
			},
			"AutoReadTime": {
				"Name": "Таймер авто прочитывания",
				"Documentation": (
					"Если настройка {{Services.VK.AutoRead}} включена, то в данной настройке Вы можете указать, через какое время после отправки сообщения собеседником, Telehooper автоматически пометит его как «прочитанное»."
				),
				"ButtonType": "enum",
				"Default": "5",
				"DependsOn": [{
					"Setting": "Services.VK.AutoRead",
					"NotEqual": "ignore"
				}],
				"EnumValues": {
					"1": "Мгновенно",
					"5": "5 секунд",
					"30": "30 секунд",
					"60": "1 минута",
					"300": "5 минут",
				},
				"VerticalButtons": True
			}
		}
	}
}
"""Древо настроек бота."""

if config.debug:
	SETTINGS_TREE.update({
		"Debug": {
			"Name": "Опции DEBUG-режима",

			"SentViaBotInform": {
				"Name": "Пересылка исходящих",
				"Documentation": (
					"При включении данной настройки, Telehooper будет пересылать отправленные Вами сообщения с помощью бота. Используется для отладки работы бота без использования сервиса."
				),
				"ButtonType": "bool",
				"Default": False
			},
			"ShowSettingPaths": {
				"Name": "Полный показ путей настроек",
				"Documentation": (
					"При включении данной настройки, Telehooper будет показывать полные пути на настройки в самом верху сообщения."
				),
				"ButtonType": "bool",
				"Default": False
			},
			"DebugTitleForDialogues": {
				"Name": "[DEBUG]-префикс в именах групп",
				"Documentation": (
					"При включении данной настройки, Telehooper будет добавлять префикс следующего вида в название подключённых к сервису группам:\n"
					"[DEBUG] Имя группы"
				),
				"ButtonType": "bool",
				"Default": False
			}
		}
	})

class SettingsHandler:
	"""
	Класс-помощник для работы с настройками.
	"""

	settings: dict
	"""Древо настроек."""

	def __init__(self, settings: dict) -> None:
		"""
		Инициализирует класс-помощник для работы с настройками.
		"""

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
			"Default": None, # Любой тип.
			"ButtonType": str
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
							raise ValueError(f"Настройка \"{value['Name']}\" не содержит свойство {name}.")

						if key_type and type(value[name]) != key_type:
							raise ValueError(f"Значение настройки \"{value['Name']}\" не является {key_type}.")

					button_type = value["ButtonType"]
					default_value = value["Default"]

					if button_type not in ["bool", "range", "enum"]:
						raise ValueError(f"Настройка имеет неизвестный тип: {value['ButtonType']}")

					default_setting_value_types = {
						"bool": bool,
						"range": int,
						"enum": str
					}

					if not isinstance(default_value, default_setting_value_types[button_type]):
						raise ValueError(f"Значение настройки \"{value['Name']}\" не является типом \"{default_setting_value_types[button_type]}\", оно равно типу \"{default_value.__class__.__name__}\"")

					if button_type == "enum":
						if not "EnumValues" in value:
							raise ValueError(f"Настройка \"{value['Name']}\" не содержит свойство EnumValues.")

						if type(value["EnumValues"]) != dict:
							raise ValueError(f"Свойство EnumValues настройки \"{value['Name']}\" не является словарём.")

						if len(value["EnumValues"]) == 0:
							raise ValueError(f"Свойство EnumValues настройки \"{value['Name']}\" пусто.")

						if default_value not in value["EnumValues"]:
							raise ValueError(f"Поле Default настройки \"{value['Name']}\" имеет такое значение, которое не существует в списке возможных (EnumValues).")
				else:
					_check(value)

		_check(self.settings)

	def fill_tree_fields(self) -> None:
		"""
		Добавляет следующие поля в древо настроек для более простой работы с ними.

		Root-объект:
		- `Paths` — лист всех существующих настроек в древе.

		Все объекты:
		- `IsValue` — является ли настройка значением (True) или папкой (False),
		- `IsFolder` — является ли настройка папкой (True) или значением (False),
		- `ParentPath` — путь к родительской папке,
		- `Path` — полный путь к настройке.
		- `PathSplitted` — список путей к настройке, разделённый по точкам.

		Настройки (`IsValue`):
		- `DependsOn` — список зависимостей настройки. (если не существовал)
		- `VerticalButtons` — являются ли кнопки настройки вертикальными (True) или горизонтальными (False). (если не существовал)
		"""

		known_paths = []
		def _fill_fields(setting: dict, path: str = "") -> None:
			items = setting.copy().items()

			for key, value in items:
				if type(value) != dict:
					continue

				if key == "EnumValues":
					continue

				is_value = "Documentation" in value
				is_folder = not is_value
				new_path = f"{path}.{key}" if path else key

				logger.debug(f"Обрабатываю {'папку с настройками' if is_folder else 'настройку'} {new_path}.")

				value["IsValue"] = is_value
				value["IsFolder"] = is_folder
				value["ParentPath"] = path
				value["Path"] = new_path
				value["PathSplitted"] = new_path.split(".")

				if is_value:
					if "DependsOn" not in value:
						value["DependsOn"] = []

					if "VerticalButtons" not in value:
						value["VerticalButtons"] = False

				known_paths.append(new_path)

				_fill_fields(value, new_path)

		# Заполняем все поля.
		_fill_fields(self.settings)

		# Сохраняем список всех путей.
		self.settings["Paths"] = known_paths

	def get_buttons_by_setting_type(self, setting: dict, current_value: Any) -> list[InlineKeyboardButton]:
		"""
		Возвращает кнопки клавиатуры в зависимости от типа настройки.

		:param setting: Настройка, для которой нужно получить кнопки.
		:param current_value: Текущее значение настройки.
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
				"⏪": setting["Min"] if current_value != setting["Min"] else None,
				"◀️": None if current_value - step < setting["Min"] else current_value - step,
				str(current_value): None,
				"▶️": None if current_value + step > setting["Max"] else current_value + step,
				"⏩": setting["Max"] if current_value != setting["Max"] else None
			}
		elif setting["ButtonType"] == "enum":
			current_value = cast(int, current_value)

			for key, value in setting["EnumValues"].items():
				buttons[value] = key if value != current_value else None
		else:
			raise ValueError(f"Неизвестный тип кнопок для настройки {setting['Path']}.")

		for text, value in buttons.items():
			callback_data = value
			is_equal = value == current_value

			if is_equal:
				callback_data = None

			btn_text = text.upper() if is_equal else text
			if is_equal and setting["VerticalButtons"]:
				btn_text = f"» {btn_text} «"

			button = InlineKeyboardButton(
				text=btn_text,
				callback_data="do-nothing" if callback_data == None else f"/settings set {setting['Path']} {callback_data}"
			)

			return_list.append(button)

		return return_list

	def get_keyboard(self, path: str | None = None, user_settings: dict | None = None) -> InlineKeyboardMarkup:
		"""
		Возвращает клавиатуру для древа настроек, по заданному пути `path` (если указан).

		:param path: Путь к настройке, которую нужно выделить.
		:param user_settings: Словарь пользовательских настроек. Если не указан, то используется значения настроек по умолчанию.
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
			setting_buttons = self.get_buttons_by_setting_type(setting, user_settings.get(path, setting["Default"]))

			keyboard_buttons = [[button] for button in setting_buttons] if setting["VerticalButtons"] else [setting_buttons]
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

	def render_tree(self, path: str | None = None, user_settings: dict = {}) -> str:
		"""
		Отрисовывает дерево настроек, выглядящее как команда `tree` в Windows.

		:param path: Путь к настройке, которую нужно выделить.
		:param user_settings: Словарь с установленными пользователем настройками. Если не указывать, то эффекта "зачёркнутой" настройки в случае зависимостей одной настройки от другой не будет.
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
				is_enabled = self.check_setting_requirements(setting["Path"], user_settings) if not is_folder and user_settings else True

				if is_folder:
					leaf_str = f"<code>{' ' * (level * 3)}{BOX_CHAR_CLOSING if is_last else BOX_CHAR_CONNECTED}{OPEN_FOLDER_EMOJI if is_selected else CLOSED_FOLDER_EMOJI}</code> {'<b>' if is_selected else ''}{setting['Name']}{'</b>:' if is_selected else ''}\n"
				else:
					leaf_str = f"<code>{' ' * (level * 3)}{BOX_CHAR_CLOSING if is_last else BOX_CHAR_CONNECTED}</code>{'<s>' if not is_enabled else ''}{SETTING_EMOJI} {'<b>' if is_selected else ''}{setting['Name']}{'</b> ◀️' if is_selected else ''}{'</s>' if not is_enabled else ''}\n"

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

		:param path: Путь к настройке.
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

		:param path: Путь к настройке.
		"""

		return self.get_setting(path)["Default"]

	def get_setting_name(self, path: str) -> str:
		"""
		Возвращает название настройки (без эмодзи) по пути `path`.
		"""

		return self.get_setting(path)["Name"]

	def replace_placeholders(self, input: str) -> str:
		"""
		Заменяет плейсхолдеры вида `{{Setting.Path.Something}}` на ссылки на эти самые настройки.

		:param input: Входная строка.
		"""

		placeholders = re.findall(r"{{(.*?)}}", input)

		for setting_path in placeholders:
			command_url = utils.create_command_url(f"/s {setting_path}")
			command_name = f"⚙️ {self.get_setting_name(setting_path)}"

			input = input.replace(
				"{{" + setting_path + "}}",
				f"<i><a href=\"{command_url}\">{command_name}</a></i>"
			)

		return input

	def check_setting_requirements(self, setting: str | dict, user_settings: dict) -> bool:
		"""
		Возвращает то, включена ли настройка или нет, в зависимости от зависимых для неё настроек.

		:param setting: Путь к настройке, либо сама настройка.
		:param user_settings: Словарь с пользовательскими значениями настроек.
		"""

		if isinstance(setting, str):
			setting = self.get_setting(setting)

		for requirement in setting["DependsOn"]:
			setting_name = requirement["Setting"]
			required_setting = self.get_setting(setting_name)

			required_set_value = user_settings.get(setting_name, required_setting["Default"])

			if "Equal" in requirement and requirement["Equal"] != required_set_value:
				return False

			if "NotEqual" in requirement and requirement["NotEqual"] == required_set_value:
				return False

		return True

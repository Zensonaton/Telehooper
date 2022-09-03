# coding: utf-8

REQUIREDENVVARS = {
	"TOKEN": "Токен Telegram-бота. Его можно получить у @BotFather.",
	"MONGODB_HOST": "Хост для подключения к MongoDB. По умолчанию localhost.",
	"MONGODB_PORT": "Порт для подключения к MongoDB. По умолчанию 27017.",
	"MONGODB_USER": "Пользователь для подключения к MongoDB. Может быть пустым. https://www.mongodb.com/docs/manual/reference/method/db.createUser/",
	"MONGODB_PWD": "Пароль пользователя для подключения к MongoDB. Может быть пустым. https://www.mongodb.com/docs/manual/reference/method/db.createUser/",
	"MONGODB_DBNAME": "Название базы данных MongoDB.",
	"MONGODB_COLLECTION": "Название коллекции в базе данных MongoDB.",
	"VKBOT_NOTIFIER_ID": "ID VK группы, в которую будет отправляться сообщение для уведомление о подключении нового пользователя. Отрицательное, числовое значение. По умолчанию 213024897. Используй число 0 для отключения.",
}

VK_OAUTH_URL = "https://oauth.vk.com/authorize?client_id=2685278&scope=69634&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1"

SETTINGS = {
	"Visual": {
		"Name": "Визуальные настройки",

		"UsePinInDialogues": {
			"Name": "Закреп со статусом",
			"Documentation": "Указывает, может ли Telehooper создавать закреплённое сообщение в новых диалогах Telegram, в которых может отображаться полезная информация:\n    <b>•</b> состояние <b>«онлайн»</b>,\n    <b>•</b> <b>имя</b> пользователя,\n    <b>•</b> статус <b>«прочитано»</b> у последнего отправленного сообщения.\nТак же рекомендуется посмотреть настройку <i>⚙️ Смещение слов в закрепе</i> (<code>/s Visual.PinCharDistance</code>) для настройки расстояния между словами в это закреплённом сообщении.",
			"Default": True
		},
		"PinOrderReversed": {
			"Name": "Порядок слов в закрепе",
			"Documentation": "При включённой опции <i>⚙️ Закреп со статусом</i>, (<code>/s Visual.UsePinInDialogues</code>) указывает, нужно ли боту поменять порядок поля статуса «онлайн» и поля «прочитано» в закреплённом сообщении.\nУвидеть как это выглядит можно в следующем сообщении, которое будет автоматически закреплено.",
			"Default": False,
			"DependsOn": [{
				"LookIn": "Visual.UsePinInDialogues",
				"EqualTo": True
			}]
		},
		"PinCharDistance": {
			"Name": "Смещение слов в закрепе",
			"Documentation": "При включённой опции <i>⚙️ Закреп со статусом</i>, (<code>/s Visual.UsePinInDialogues</code>) указывает расстояние между словами, указывающих состояние «онлайн», имя пользователя, и статус «прочитано» последнего отправленного сообщения.\n\nДанная опция может быть нужна, если закреплённое сообщение отображается на вашем экране некорректно. К сожалению, реализовать отдельные «профиля» для ПК и телефона невозможно, поскольку в Telegram нет возможности узнать с какого именно устройства пользователь просматривает диалог.\nУвидеть как это выглядит можно в следующем сообщении, которое будет автоматически закреплено.",
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
			"Documentation": "Указывается, может ли Telehooper хранить токены авторизации <a href=\"https://dev.vk.com/api/access-token/getting-started\"><i>[Документация ВК]</i></a> в его базе данных для автоматического процесса восстановления сессий сервисов в случае перезагрузки, вызванной, к примеру, обновлением бота.\n\nВыключив эту опцию <b>вы повысите безопасность своих сервисов</b> в случае взлома базы данных бота, однако, после своей перезагрузки Telehooper не сумеет переподключиться <b>ко всем сервисам</b>, что были подключены ранее, и поэтому Вам придётся снова производить процедуру авторизации.\nИзменения этой настройки будут применены мгновенно.",
			"Default": True
		},
		"MediaCache": {
			"Name": "Кэш медиа",
			"Documentation": "Определяет, может ли Telehooper хранить ID отправленных и/ли полученных медиа, <i>(например, фото, видео, файлов, ...)</i> с целью кэширования, уменьшения нагрузки и ускорения работы бота.\nЗначение данной опции не влияет на стикеры; из-за технических ограничений, они будут кэшироваться всегда.\n\nС точки зрения безопасности, кэшированные ID файлов зашифрованы таким образом, что бы расшифровать их можно было только в том случае, если бот получил точно такой же файл, как и в базе данных.\n<i>Пояснение:</i> При получении нового медиа бот хэширует <code>unique_file_id</code> используя SHA256, а ID медиа в сервисе шифруется с ключём, равным оригинальному значению <code>unique_file_id</code>.",
			"Default": True
		}
	},

	"Services": {
		"Name": "Настройки сервисов",

		"MarkAsReadButton": {
			"Name": "Кнопка «прочитать»",
			"Documentation": "Включает или отключает кнопку «Прочитать» возле новых сообщений, отправленных собеседником диалога. Данная кнопка показана под самым «последним» отправленным собеседником сообщением, и она автоматически скрывается при нажатии. Данная кнопка выполняет такое же действие, как и команда <code>/read</code>.\n\nТак же рекомендуется уделить внимание на настройку <i>⚙️ Закреп со статусом</i>, (<code>/setting Visual.UsePinInDialogues</code>) ведь в закреплённом сообщении показана информации о том, было прочитано сообщение или нет.",
			"Default": True
		},
		"WaitToType": {
			"Name": "Задержка для «печати»",
			"Documentation": "Включает специальную задержку в <code>500</code>мс (<code>0.5</code> секунды) перед отправкой сообщения. Перед отправкой сообщения, в сервисе сообщение сразу отмечается как «прочитанное», и начинается анимация «пользователь печатает».",
			"Default": False
		}
	},

	"Other": {
		"Name": "Другое",
	},

	"TEST": {
		"Name": "Тест вложенности",

		"TEST": {
			"Name": "Тест №1",

			"TEST": {
				"Name": "Тест №2",

				"TEST": {
					"Name": "Тест №3",

					"TEST": {
						"Name": "Тест №4",

						"TEST": {
							"Name": "Тест №5",
						}
					}
				}
			},
			"TEST2": {
				"Name": "Тест №2",

				"TEST": {
					"Name": "Тест №3",

					"TEST": {
						"Name": "Тест №4",

						"TEST": {
							"Name": "Тест №5",
						}
					}
				}
			},
			"TEST3": {
				"Name": "Тест №2",

				"TEST": {
					"Name": "Тест №3",

					"TEST": {
						"Name": "Тест №4",

						"TEST": {
							"Name": "Тест №5",
						}
					}
				}
			}
		}
	}
}

class officialVKAppCreds:
	"""
	Класс/Enum для хранения официальных данных приложений ВК. Необходимо для авторизации через логин-пароль.
	"""

	# Взято из:
	# https://github.com/negezor/vk-io/blob/master/packages/authorization/src/constants.ts#L63-L88

	class appCredential:
		"""
		Класс с информацией о приложении ВК.
		"""

		clientID: int
		clientSecret: str

		def __init__(self, clientID: int, clientSecret: str) -> None:
			self.clientID = clientID
			self.clientSecret = clientSecret

	ANDROID = appCredential(2274003, "hHbZxrka2uZ6jB1inYsH")
	WINDOWS = appCredential(3697615, "AlVXZFMUqyrnABp8ncuU")
	WINDOWS_PHONE = appCredential(3502557, "PEObAuQi6KloPM4T30DV")
	IPHONE = appCredential(3140623, "VeWdmVclDCtn6ihuP1nt")
	IPAD = appCredential(3682744, "mY6CDUswIVdJLCD3j15n")
	VK_ME = appCredential(6146827, "qVxWRF1CwHERuIrKBnqe")

class InlineButtonCallbacks:
	class CommandCallers:
		ME = "command_self"
		THIS = "command_this"
		CONVERT = "command_convert_to_dialogue"

	class CommandActions:
		CONVERT_TO_DIALOGUE = "action_convert_to_dialogue"
		DISCONNECT_SERVICE = "action_disconnect_service"
		DIALOGUE_SELECT_VK = "action_dialogue-vk:"
		CONVERT_TO_REGULAR_GROUP = "action_convert_to_group"
		GOTO_SETTING = "action_gotosetting:"

	class CommandMenus:
		VK_LOGIN_VKID = "menu_login_vkid"
		VK_LOGIN_PASSWORD = "menu_login_pass"

	class CancelAction:
		CANCEL_DELETE_MESSAGE = "cancel_delete_message"
		CANCEL_EDIT_MESSAGE = "cancel_edit_message"
		CANCEL_HIDE_BUTTONS = "cancel_hide_buttons"

	DO_NOTHING = "do_nothing"

class AccountDisconnectType:
	INITIATED_BY_USER = 1
	EXTERNAL = 2
	SILENT = 3
	ERRORED = 4

class MAPIServiceType:
	VK = 1

class CommandThrottleNames:
	VK_LOGIN = "vklogin"
	VK_LOGIN_VKID = "vkloginviavkid"
	DIALOGUE_CONVERT = "grouptodialogueconvert"
	SERVICES_LIST = "services"
	THIS_DIALOGUE = "this"

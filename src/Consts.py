# coding: utf-8

FAQ_INFO = {
	"1. Основная информация": (
		"<b>1. Основная информация</b>.\n"
		"\n"
		"Telehooper — бот, который позволяет Вам подключаться к различным сервисам и получать их сообщения прямо в Telegram.\n"
		"\n"
		"🤝 <b>Ваш персональный посредник</b>.\n"
		"Telehooper выступает в роли посредника между вами и другими сервисами. Он пересылает сообщения туда-сюда, обеспечивая коммуникацию между вами и сервисами, которые вы подключаете.\n"
		"<i>Более подробную информацию о сервисах можно прочитать в пункте «3. Поддерживаемые сервисы»</i>.\n"
		"\n"
		"🔓 <b>Открытость && прозрачность</b>.\n"
		"Telehooper — это проект с <a href=\"https://github.com/Zensonaton/Telehooper\">открытым исходным кодом</a>. Это означает, что Вы можете посмотреть на исходный код и убедиться, что он не делает ничего, чего не должен делать. Помимо этого, Вы имеете полное право запустить данного бота локально, на своём личном сервере.\n"
		"\n"
		"🔐 <b>Безопасность</b>.\n"
		"Telehooper старается держать Ваши данные в безопасности. В случае каких-либо инцидентов связанных с безопасностью мы обязательно оповестим Вас.\n"
		"<i>Более подробную информацию связанную с безопасностью можно прочитать в пункте «4. Безопасность»</i>.\n"
		"\n"
		"ℹ️ Продолжайте чтение, используя кнопки ниже, чтобы узнать о других важных возможностях Telehooper."
	),
	"2. Принцип работы": (
		"<b>2. Принцип работы</b>.\n"
		"\n"
		"Бот Telehooper работаем по принципу «посредника» между Вами и сервисами, которые Вы подключаете. Он пересылает сообщения туда-сюда, обеспечивая коммуникацию между Вами и сервисами, которые Вы подключаете.\n"
		"Однако, возникает вопрос,\n"
		"— <i>«а как именно нужно получать новые сообщения? в чём принцип работы бота?»</i>\n"
		"\n"
		"В Telehooper, после подключения сервиса к боту есть 2 метода получения новых сообщений:\n"
		" • <b>Диалог сервиса</b>: Для каждого отдельного диалога у сервиса можно завести отдельную Telegram-группу, которая будет иметь имя и аватар подключённого диалога.\n"
		" • <b>Топик сервиса</b>. Для каждого отдельного диалога используется отдельный топик в созданном Вами канале с включёнными топиками.\n"
		"\n"
		"Примеры ситуаций:\n"
		" 1. Вы общаетесь с Иваном Ивановым, который пользуется ВКонтакте, но не использует Telegram. Если Вы общаетесь с данным человеком очень часто, то рекомендуется использовать <b>сервис-диалог</b>.\n"
		" 2. Вы общаетесь с Андреем Андреевым. Данный человек общается с Вами только для отправки мемов, и его общение не столь важно и происходит не столь часто. В таком случае лучше использовать <b>сервис-топик</b>.\n"
		" 3. Третьего случая быть не должно.\n"
	),
	"3. Поддерживаемые сервисы": (
		"<b>3. Поддерживаемые сервисы</b>.\n"
		"\n"
		"Ввиду разных возможностей/ограничений (как со стороны Telegram, так и сервисов), не весь функционал может корректно работать либо вообще присутствовать. Отдельные сервисы могут создавать свои собственные ограничения, из-за которых часть функционала может вовсе отсутствовать внутри бота.\n"
		"\n"
		"Общий список ограничений бота Telehooper:\n"
		" • <b>Отсутствие показа статуса «печати» у сервисов</b>: Печатая в Telegram, Вы не увидите статус «печати» внутри сервиса, к которому Вы подключёны. Увы, но Telegram Bot API не даёт информацию ботам о статусе печати пользователей.\n"
		" • <b>Лимиты на размеры файлов</b>: Telegram ограничивает размер на отправку файлов для ботов до 50 мегабайт, пока как на скачивание лимит ещё ниже, - 20 мегабайт. Источник: <a href=\"https://core.telegram.org/bots/faq#handling-media\">Telegram Bot API FAQ</a>.\n"
		" • <b>Отсутствие реакций</b>: Ботам в Telegram не дозволено получать события а так же список реакций под сообщениями. Это значит, что поддержка реакций отсутствует.\n"
		" • <b>Показ состояния «онлайн»</b>: По причинам безопасности, Telegram не передаёт ботам информацию о состоянии «онлайн». Это значит, что находясь «онлайн» в Telegram, Вы не окажетесь «онлайн» в подключённых сервисах.\n"
		" • <i>...и многие другие</i>.\n"
		"\n"
		"Telehooper поддерживает следующие сервисы:\n"
		" • <a href=\"vk.com\">ВКонтакте</a>. Подробности: <a href=\"https://github.com/Zensonaton/Telehooper/blob/rewrite/src/services/vk/README.md\">ссылка</a>.\n"
		"\n"
		"Сервисы, поддержка которых планируется в будущем:\n"
		" • Whatsapp. Подробности: <a href=\"https://github.com/Zensonaton/Telehooper/blob/rewrite/src/services/whatsapp/README.md\">ссылка</a>.\n"
		" • Discord. Подробности: <a href=\"https://github.com/Zensonaton/Telehooper/blob/rewrite/src/services/discord/README.md\">ссылка</a>.\n"
	),
	"4. Безопасность": (
		"<b>4. Безопасность</b>.\n"
		"\n"
		"Разработчики бота Telehooper делают все возможное, чтобы обеспечить безопасность ваших данных. Однако, абсолютная защита от взломов невозможна. Пожалуйста, запомните следующее предупреждение:\n"
		"\n"
		"⚠️ <b><u>ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ: РАЗРАБОТЧИКИ БОТА НЕ МОГУТ ГАРАНТИРОВАТЬ БЕЗОПАСНОСТЬ ВАШИХ ДАННЫХ ПРИ АВТОРИЗАЦИИ В БОТЕ. В СЛУЧАЕ ВЗЛОМА БОТА СУЩЕСТВУЕТ РИСК ТОГО, ЧТО РАЗРАБОТЧИКИ НЕ СМОГУТ ПРЕДУПРЕДИТЬ ВАС О ПРОИЗОШЕДШЕМ.</u></b> ⚠️\n"
		"\n"
		"Telehooper <b>не хранит</b> ваши логины и пароли. После авторизации, Вы передаете боту токен, который используется для подключения к сервису. Этот токен используется для выполнения определенных действий, таких как отправка сообщений. В токене не содержится информации о вашем пароле. Примером использования токенов является ВКонтакте, подробнее: <a href=\"https://dev.vk.com/api/access-token/getting-started\">документация VK API</a>.\n"
		"\n"
		"Telehooper хранит токены авторизации в базе данных для автоматического повторного подключения к аккаунтам после перезагрузки бота. Однако, у вас есть возможность использовать режим гостя и не сохранять токены в базе данных. Для этого вы можете выключить опцию <i>⚙️ Хранение токенов в БД</i> (<code>/s Security.StoreTokens</code>). Подробнее об этом написано ниже.\n"
		"\n"
		"Telehooper использует базу данных CouchDB, где хранятся следующие данные:\n"
		" • <b>Токены авторизации</b>: Токены авторизации используются для подключения к сервисам. При включенной опции <i>⚙️ Хранение токенов в БД</i> (<code>/s Security.StoreTokens</code>), токены авторизации хранятся в базе данных и автоматически подключаются к сервисам после перезагрузки бота.\n"
		" • <b>Идентификаторы медиа</b>: Идентификаторы медиа используются для кэширования отправленных или полученных через бота медиафайлов. При включенной опции <i>⚙️ Кэш медиа</i> (<code>/s Security.MediaCache</code>), идентификаторы медиа хранятся в базе данных. Имея полный доступ к серверу, получить доступ к медиа невозможно.\n"
		"\n"
		"Telehooper НЕ хранит:\n"
		" • Ваш логин/пароль, Telehooper хранит <a href=\"https://dev.vk.com/api/access-token/getting-started\">токены авторизации</a>.\n"
		" • Ваши сообщения, Telehooper хранит их ID.\n"
		"\n"
		"Теоретические случаи взлома бота:\n"
		" 1. <b>Взлом базы данных бота</b>: В таком случае злоумышленник может получить зашифрованные токены авторизации, но он не сможет с ними сделать ничего. Ваши данные остаются в безопасности.\n"
		" 2. <b>Доступ к файлам бота</b>: В таком случае злоумышленник может получить ключ для расшифровки токенов авторизации, но возможно, что самого токена у него не будет. Ваши данные остаются в безопасности.\n"
		" 3. <b>Полный доступ к серверу бота</b>: Этот случай крайне маловероятен. В таком случае злоумышленник может расшифровать токены и получить доступ к вашим аккаунтам. Ваши данные будут под угрозой, однако администраторы смогут заметить подозрительную активность и предупредить вас о ней.\n"
		"\n"
		"ℹ️ Напоминание: У бота открытый исходный код, Вы можете проверить то, что бот не делает ничего, чего не должен делать. Помимо этого, Вы имеете полное право запустить данного бота локально, на своём личном сервере. Проверьте вкладку «6. Контакты» для получения дополнительной информации."
	),
	"5. Начало работы с ботом": (
		"<b>5. Начало работы с ботом</b>.\n"
		"\n"
		"Как Вам уже известно, задача Telehooper — быть «посредником» для пересылки сообщений из сервисов. В данном разделе описано именно то, как начать получать сообщения из сервисов в Telegram.\n"
		"\n"
		"<b><u>#1</u>. Подключение сервиса к Telehooper</b>. Для начала, Telehooper'у необходимо получить доступ к Вашему аккаунту для получения сообщений. Для подключения аккаунта нужно сделать следующее:\n"
		"  1. Пропишите команду /connect в этом же чате.\n"
		"  2. Выберите нужный Вам сервис в списке.\n"
		"  3. Следуйте инструкциям, которые будут показаны в чате.\n"
		"\n"
		"Если всё будет в порядке, то нужный Вам сервис будет подключен к Telehooper, и Вы сможете увидеть это подключение в команде /me, либо же команде /connect.\n"
		"\n"
		"<b><u>#2</u>. Создание диалога</b>. После подключения сервиса Вам необходимо начать получать новые сообщения. В боте Telehooper для каждого отдельного диалога сервиса необходимо создавать отдельную группу и дальше привязывать её к боту.\n"
		"  1. Создайте группу в Telegram. Внимание, речь идёт именно о группе, не канале!\n"
		"  2. Добавьте в группу бота Telehooper. Откройте настройки созданной группы и дальше добавьте @telehooper_bot.\n"
		"  3. Дайте боту права администратора.\n"
		"  4. Следуйте отправленными ботами инструкциям, либо же, как альтернатива, используйте команду <code>/convert</code>.\n"
		"  5. Следуйте всем последующими инструкциями, которые зависят от Вашего выбора.\n"
		"\n"
		"Теперь вы готовы начать использовать бота Telehooper и получать сообщения из различных сервисов прямо в Telegram! 😌\n"
	),
	"6. Контакты": (
		"<b>6. Контакты</b>.\n"
		"\n"
		"В данном разделе записаны разные ссылки.\n"
		" • Группа новостей: @telehooper_news.\n"
		" • Разработчик бота: @zensonaton.\n"
		" • Исходный код бота: <a href=\"https://github.com/Zensonaton/Telehooper\">Zensonaton/Telehooper</a>.\n"
		" • Баг-репорты и предложения: <a href=\"https://github.com/Zensonaton/Telehooper/issues\">Github Issues</a>.\n"
	)
}
"""Информация для команды /help."""

class CommandButtons:
	"""
	Класс с наименования для кнопок.
	"""

	HELP = "ℹ️ Информация"
	CONNECT = "🌐 Подключить сервис"
	SETTINGS = "⚙️ Настройки"
	ME = "👤 Ваш профиль"
	THIS = "📩 Этот диалог"

COMMANDS = {
	"start": "Стартовая команда бота",
	"help": "Помощь по боту",
	"settings": "Настройки бота",
	"me": "Просмотр профиля и управление подключёнными сервисами",
	"connect": "Подключение сервиса к боту"
}
"""Базовый список команд в боте, который виден всем пользователям вне зависимости от scope."""

COMMANDS_USERS_GROUPS = {
	**COMMANDS,

	"this": "Конвертирование данной группы в диалог сервиса"
}
"""Список команд в боте, который виден пользователям, которые находятся в группе."""

COMMANDS_USERS_GROUPS_CONVERTED = {
	**COMMANDS,

	"this": "Управление данным диалогом"
}
"""Список команд в боте, который виден пользователям, которые находятся в группе-диалоге."""

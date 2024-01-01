# Telehooper

![Лого бота Telehooper](resources/logo.png)

[Telehooper - это Telegram-бот](https://t.me/telehooper_bot) для подключения различных сервисов для получения и/ли отправки сообщений.

Дополнительная информация по боту доступна на сайте <http://telehooper.com>.

## Инструкции по установке и запуску бота

> [!NOTE]
> Если Вы просто хотите воспользоваться ботом, то Вы можете написать [@telehooper_bot в Telegram](https://t.me/telehooper_bot).

Любой пользователь бота имеет полное право запустить бота локально: будь то для разработки или личного использования. Если Вы планируете запустить бота для личного использования, то, пожалуйста, не делайте его «публичным», давая доступ к «личной» версии бота другим пользователям; поддержите разработчика бота, поделившись публичным ботом, `@telehooper_bot`.

1. Вам необходимо установить и настроить базу данных [CouchDB](https://couchdb.apache.org/). В случае, если Вы используете Docker, то Вы можете запустить БД как контейнер:

   ```bash
   sudo docker run -d --name couchdb --restart=always -p 5984:5984 -e COUCHDB_USER=admin -e COUCHDB_PASSWORD=p@$$w0rd! couchdb:latest
   ```

   Вместо `p@$$w0rd!`, очевидно, стоит установить более длинный и изощрённый пароль, поскольку этим паролем Вы будете заходить как Администратор БД.

   Запустив БД, Вы можете попасть в панель Администратора, зайдя на <http://localhost:5984/_utils/>. Авторизуйтесь на странице, введя данные, которые Вы передали при запуске контейнера (поля `COUCHDB_USER` и `COUCHDB_PASSWORD`).

   Перед Вами будет пустой список баз данных. Вам необходимо создать отдельного пользователя БД, который будет использоваться для бота Telehooper. Для этого, нажмите на кнопку "Create Database", и в поле "database-name" введите `_users`. Ничего не меняя, нажмите на "Create". Откройте новосозданную БД "_users".

   Нажмите на "Create Document", введя туда следующее:

   ```json
   {
       "_id": "org.couchdb.user:telehooper",
       "name": "telehooper",
       "password": "p@$$w0rd!",
       "roles": [],
       "type": "user"
   }
   ```

   Нажав на "Create Document", Вы создадите пользователя `telehooper` с паролем `p@$$w0rd!`.

   Теперь Вам необходимо создать БД `telehooper-bot`. Для этого обратитесь к списку БД, и нажмите на "Create Database". Введите туда `telehooper-bot`, и, опять же, ничего не меняя, нажмите на "Create".

   Вы создали БД `telehooper-bot`. Теперь Вам необходимо дать пользователю `telehooper` доступ к данной БД, для этого нажмите на "Permissions", и в разделе Admins -> Users, введите в текстовое поле "Username" пользователя `telehooper`, нажав после этого на кнопку "Add User".

2. Создайте Telegram-бота у [@BotFather](https://t.me/botfather).

   Обратитесь к официальному боту для создания и управления Telegram-ботами [@BotFather](https://t.me/botfather). Прописав команду `/newbot`, проследуйте инструкциям, создав бота.

   После создания бота, BotFather выдаст токен, который выглядит примерно так: `12345678:abcdef...`. Этот токен необходимо сохранить.
3. Загрузите исходный код бота.

   Для загрузки исходного кода бота нужно прописать следующие команды:

   ```bash
   git clone https://github.com/Zensonaton/Telehooper.git
   cd Telehooper
   ```

4. Создайте `.env`-файл с конфигурацией в папке с ботом. Примерное его содержимое:

   ```env
   telegram_token=12345678:abcdef...
   couchdb_name=test
   couchdb_user=test
   couchdb_password=test
   token_encryption_key=abcdefg123456789
   ```

   > [!WARNING]
   > Вероятнее всего, данный пункт не будет отображать актуальное содержимое файла `.env`. Рекомендуется обратиться к файлу [config.py](src/config.py), поскольку в нём расположены все поля для `.env`-файла, вместе с их подробными описаниями.

5. Установите [Python как минимум 3.10 версии](https://www.python.org/).
6. Установите зависимости для Telehooper'а:

   ```bash
   pip install -r requirements.txt
   ```

7. Запустите бота:

   ```python
   python src/main.py
   ```

### (Опционально) Запустите Local Bot API

Публичный API для работы с ботами Telegram, Bot API, [имеет ограничения на размер скачиваемых и отправляемых файлов в 20 и 50 МБ](https://core.telegram.org/bots/faq#how-do-i-upload-a-large-file). Что бы обойти это ограничение, можно запустить локальную версию Bot API которую зовут Local Bot API. Настроив Local Bot API, и подключив его к Telehooper'у, Вы сможете увеличить лимит до 250 МБ.

1. Создайте Telegram-приложение. Сделать это можно на <https://my.telegram.org/>, нажав на "API development tools". Создав приложение, скопируйте поля `api_id` и `api_hash`.
2. Создайте файл `docker-compose.yml` со следующими полями:

   ```yml
   version: "3.8"

   services:
      telegram-bot-api:
         image: aiogram/telegram-bot-api:latest
         environment:
            TELEGRAM_API_ID: "..."
            TELEGRAM_API_HASH: "..."
            TELEGRAM_LOCAL: Yes

         volumes:
            - telegram-bot-api-data:/var/lib/telegram-bot-api
         ports:
            - "8081:8081"
            - "8082:8082"
         restart: unless-stopped

   nginx:
      image: nginx:latest
      volumes:
         - telegram-bot-api-data:/telegram-bot-api-data
         - ./nginx.conf:/etc/nginx/conf.d/default.conf
      ports:
         - "8080:8080"
      restart: unless-stopped

   volumes:
      telegram-bot-api-data:
         external: true
   ```

   Не забудьте заменить поля `TELEGRAM_API_ID` и `TELEGRAM_API_HASH`.

3. Создайте файл `nginx.conf` со следующим содержанием:

   ```conf
   server {
      listen 8080;

      server_name localhost;
      client_max_body_size 1500m;

      location / {
         rewrite ^.*telegram-bot-api(.*)$ /$1 last;
         root /telegram-bot-api-data/;
         index index.html;
         try_files $uri $uri/ =404;
      }

      error_page 500 502 503 504 /50x.html;
      location = /50x.html {
         root /usr/share/nginx/html;
      }
   }
   ```

4. Запустите Docker-контейнер:

   ```bash
   docker compose up -d
   ```

5. Укажите URL Local Bot API в `.env`-файле бота:

   ```env
   telegram_local_api_url=http://localhost:8081
   telegram_local_file_url=http://localhost:8080
   ```

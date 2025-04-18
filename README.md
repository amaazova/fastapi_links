# FastAPI URL Shortener API

Этот проект представляет собой API для сервиса сокращения URL, реализованный с использованием FastAPI, SQLAlchemy и Celery. API позволяет:

- Регистрировать новых пользователей и выполнять аутентификацию.
- Генерировать access и refresh токены для доступа к защищённым эндпоинтам.
- Создавать, обновлять, удалять и получать статистику по сокращённым URL.
- Работать как с приватными ссылками (привязанными к пользователю), так и с публичными.
- Автоматически очищать просроченные и неактивные ссылки с помощью фоновых задач (Celery).

# Структура проекта 

```
fastapi-url-shortener/
├── routers/                  # Эндпоинты (маршруты) API
│   ├── __init__.py
│   ├── links.py             # Маршруты управления ссылками
│   └── users.py             # Маршруты регистрации и аутентификации пользователей
├── screenshots/             # Скриншоты документации API (Swagger UI)
├── .gitignore               # Игнорируемые файлы в Git
├── Dockerfile               # Файл сборки Docker-образа для приложения
├── README.md                # Описание проекта, примеры и инструкция
├── auth.py                  # Аутентификация (JWT), хеширование паролей, безопасность
├── config.py                # Конфигурационные переменные проекта
├── database.py              # Подключение и взаимодействие с базой данных (SQLAlchemy)
├── docker-compose.yml       # Запуск всех компонентов через Docker Compose
├── main.py                  # Главный файл приложения FastAPI (точка входа)
├── models.py                # Описание моделей базы данных (таблицы SQLAlchemy)
├── requirements.txt         # Список зависимостей проекта
├── schemas.py               # Валидация данных и схемы Pydantic для запросов и ответов
├── tasks.py                 # Фоновые задачи (Celery) для очистки ссылок
└── utils.py                 # Вспомогательные функции, такие как генерация коротких ссылок
```



---

## Оглавление

- [API эндпоинты](#api-эндпоинты)
  - [Пользовательские эндпоинты](#пользовательские-эндпоинты)
  - [Эндпоинты для ссылок](#эндпоинты-для-ссылок)
  - [Фоновые задачи](#фоновые-задачи)
- [Примеры запросов](#примеры-запросов)
- [Инструкция по запуску](#инструкция-по-запуску)
- [Описание базы данных](#описание-базы-данных)
  - [Таблица `users`](#таблица-users)
  - [Таблица `links`](#таблица-links)

---

## API эндпоинты

### Пользовательские эндпоинты

#### Регистрация пользователя
- **Метод:** `POST`
- **Путь:** `/users/register`
- **Описание:** Регистрация нового пользователя.
- **Тело запроса (JSON):**
  - `username` (string) — имя пользователя.
  - `password` (string) — пароль.
- **Ответ:** Объект пользователя с полями:
  - `id`
  - `username`

---

#### Аутентификация и получение токенов
- **Метод:** `POST`
- **Путь:** `/users/token`
- **Описание:** Аутентификация пользователя и получение access/refresh токенов.
- **Тело запроса:** Данные формы (OAuth2PasswordRequestForm):
  - `username`
  - `password`
- **Ответ:** JSON объект с:
  - `access_token`
  - `refresh_token`
  - `token_type` (обычно `"bearer"`)

---

#### Обновление токена
- **Метод:** `POST`
- **Путь:** `/users/token/refresh`
- **Описание:** Обновление access токена с использованием refresh токена.
- **Тело запроса (JSON):**
  - `refresh_token` — refresh токен.
- **Ответ:** JSON объект с новыми:
  - `access_token`
  - `refresh_token`
  - `token_type`

---

#### Получение ссылок пользователя
- **Метод:** `GET`
- **Путь:** `/users/links`
- **Описание:** Получение списка ссылок, созданных аутентифицированным пользователем.
- **Аутентификация:** Требуется Bearer токен.
- **Ответ:** Массив объектов ссылок.

---

### Эндпоинты для ссылок

#### Создание сокращённой ссылки (для аутентифицированных пользователей)
- **Метод:** `POST`
- **Путь:** `/shorten`
- **Описание:** Создание новой сокращённой ссылки, привязанной к пользователю.
- **Аутентификация:** Bearer токен обязателен.
- **Тело запроса (JSON):**
  - `original_url` (string, URL) — оригинальный URL.
  - `custom_alias` (string, опционально) — пользовательский alias (только алфавитно-цифровые символы).
  - `category` (string, опционально) — категория ссылки.
  - `expires_at` (datetime, опционально) — дата истечения срока действия. Поддерживаются различные форматы:
    - `YYYY-MM-DDTHH:MM:SS.SSSZ`
    - `DD.MM.YYYY HH:MM`
    - `YYYY-MM-DD HH:MM:SS`
    - `YYYY-MM-DDTHH:MM:SS`
    - `YYYY-MM-DD`
  - `is_public` (boolean, опционально) — флаг, указывающий, является ли ссылка публичной (по умолчанию `false`).
- **Ответ:** Объект созданной ссылки со следующими полями:
  - `id`
  - `original_url`
  - `short_code`
  - `created_at`
  - `expires_at`
  - `redirect_count`
  - `last_redirect_at`
  - `owner_id`
  - `category`
  - `is_public`

---

#### Создание публичной сокращённой ссылки
- **Метод:** `POST`
- **Путь:** `/shorten/public`
- **Описание:** Создание публичной сокращённой ссылки. Здесь не требуется аутентификация.
- **Тело запроса:** Как и для обычного создания ссылки, но `owner_id` будет `null`, а флаг `is_public` установлен в `true`.
- **Ответ:** Объект созданной ссылки.

---

#### Поиск ссылок
- **Метод:** `GET`
- **Путь:** `/search`
- **Описание:** Поиск ссылок по запросу в полях `original_url` или `short_code`.
- **Параметры запроса (Query):**
  - `query` (string) — поисковая строка.
  - `skip` (integer, опционально, по умолчанию `0`) — смещение.
  - `limit` (integer, опционально, по умолчанию `10`) — количество результатов.
- **Аутентификация:** Опционально. Если пользователь аутентифицирован, возвращаются как публичные, так и принадлежащие пользователю ссылки; иначе – только публичные.
- **Ответ:** Массив объектов ссылок.

---

#### Получение ссылок по категории
- **Метод:** `GET`
- **Путь:** `/category/{category}`
- **Описание:** Получение списка ссылок, отфильтрованных по указанной категории.
- **Аутентификация:** Опционально (аналогично поиску).
- **Ответ:** Массив объектов ссылок.

---

#### Получение статистики по ссылке
- **Метод:** `GET`
- **Путь:** `/{short_code}/stats`
- **Описание:** Получение детальной информации и статистики (количество редиректов, даты создания и т.д.) для ссылки по её короткому коду.
- **Ответ:** Объект ссылки со всеми полями.

---

#### Генерация QR-кода
- **Метод:** `GET`
- **Путь:** `/{short_code}/qrcode`
- **Описание:** Генерация и возврат QR-кода для ссылки в формате PNG.
- **Ответ:** Поток данных с изображением QR-кода.

---

#### Обновление ссылки
- **Метод:** `PUT`
- **Путь:** `/{short_code}`
- **Описание:** Обновление данных существующей ссылки. Обновление доступно только для владельца ссылки.
- **Аутентификация:** Требуется Bearer токен.
- **Тело запроса:** JSON с обновляемыми полями, аналогичными схеме создания ссылки.
- **Ответ:** Обновлённый объект ссылки.

---

#### Удаление ссылки
- **Метод:** `DELETE`
- **Путь:** `/{short_code}`
- **Описание:** Удаление ссылки. Доступно только владельцу.
- **Аутентификация:** Требуется Bearer токен.
- **Ответ:** JSON с сообщением об успешном удалении.

---

#### Редирект по короткому коду
- **Метод:** `GET`
- **Путь:** `/{short_code}`
- **Описание:** Перенаправляет запрос на оригинальный URL, увеличивая счётчик редиректов и обновляя время последнего редиректа.
- **Ответ:** HTTP-редирект на оригинальный URL.

---

### Фоновые задачи

Для поддержки актуальности данных используются фоновые задачи, запускаемые через Celery:

- **cleanup_expired_links_task**: Удаляет ссылки, у которых истёк срок действия (`expires_at` меньше текущей даты).
- **cleanup_inactive_links_task**: Удаляет неактивные ссылки (если с момента последнего редиректа или создания прошло более заданного количества дней).

---
## Примеры-запросов

### 1. Регистрация пользователя

**Запрос**
```bash
curl -X POST "http://localhost:8000/users/register" \
  -H "Content-Type: application/json" \
  -d '{
        "username": "yuzuru_hanyu",
        "password": "secure_password"
      }'
```

**Пример ответа**
```json
{
  "id": 1,
  "username": "yuzuru_hanyu"
}
```

> **Пояснение:**  
Создаётся новый пользователь с именем yuzuru_hanyu.

---

### 2. Аутентификация (получение токенов)

**Запрос**
```bash
curl -X POST "http://localhost:8000/users/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=yuzuru_hanyu&password=secure_password"
```

**Пример ответа**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....",
  "token_type": "bearer"
}
```

> **Пояснение:**  
Полученные токены используются для доступа к защищённым эндпоинтам.

---

### 3. Получение списка ссылок пользователя

**Запрос**
```bash
curl -X GET "http://localhost:8000/users/links" \
  -H "Authorization: Bearer <access_token>"
```

**Пример ответа**
```json
[
  {
    "id": 1,
    "original_url": "https://example.com",
    "short_code": "privateLink",
    "created_at": "2025-01-01T12:00:00",
    "expires_at": "2025-12-31T23:59:59",
    "redirect_count": 0,
    "last_redirect_at": null,
    "owner_id": 1,
    "category": "News",
    "is_public": false
  }
]
```

> **Пояснение:**  
Возвращается список ссылок, созданных пользователем yuzuru_hanyu.

---

### 4. Создание сокращённой ссылки (приватной, для авторизованных пользователей)

**Запрос**
```bash
curl -X POST "http://localhost:8000/shorten" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
        "original_url": "https://example.com",
        "custom_alias": "privateLink",
        "category": "News",
        "expires_at": "2025-12-31T23:59:59",
        "is_public": false
      }'
```

**Пример ответа**
```json
{
  "id": 1,
  "original_url": "https://example.com",
  "short_code": "privateLink",
  "created_at": "2025-01-01T12:00:00",
  "expires_at": "2025-12-31T23:59:59",
  "redirect_count": 0,
  "last_redirect_at": null,
  "owner_id": 1,
  "category": "News",
  "is_public": false
}
```

> **Пояснение:**  
Ссылка создаётся с кастомным alias privateLink и привязывается к зарегистрированному пользователю yuzuru_hanyu.

---

### 5. Создание публичной сокращённой ссылки (без авторизации)

**Запрос:**
```bash
curl -X POST "http://localhost:8000/shorten/public" \
  -H "Content-Type: application/json" \
  -d '{
        "original_url": "https://public-example.com",
        "custom_alias": "publicLink",
        "category": "Public",
        "expires_at": "2025-12-31T23:59:59",
        "is_public": true
      }'
```

**Пример ответа:**
```json
{
  "id": 2,
  "original_url": "https://public-example.com",
  "short_code": "publicLink",
  "created_at": "2025-01-02T12:00:00",
  "expires_at": "2025-12-31T23:59:59",
  "redirect_count": 0,
  "last_redirect_at": null,
  "owner_id": null,
  "category": "Public",
  "is_public": true
}
```

> **Пояснение:** Публичная ссылка создаётся без привязки к пользователю (`owner_id` равно `null`).

### 6. Поиск ссылок

#### 6.1 Поиск публичных ссылок (без авторизации)
```bash
curl -X GET "http://localhost:8000/search?query=example"
```

#### 6.2 Поиск ссылок для авторизованного пользователя
```bash
curl -X GET "http://localhost:8000/search?query=example&skip=0&limit=10" \
  -H "Authorization: Bearer <access_token>"
```

> **Пояснение:** Параметры `skip` и `limit` используются для пагинации.

### 7. Получение статистики по ссылке

#### 7.1 Статистика по приватной ссылке (с авторизацией)
```bash
curl -X GET "http://localhost:8000/privateLink/stats" \
  -H "Authorization: Bearer <access_token>"
```

#### 7.2 Статистика по публичной ссылке (без авторизации)
```bash
curl -X GET "http://localhost:8000/publicLink/stats"
```

> **Пояснение:** Статистика для приватных ссылок доступна только с авторизацией.

### 8. Генерация QR-кода для ссылки

#### 8.1 QR-код для приватной ссылки (с авторизацией)
```bash
curl -X GET "http://localhost:8000/privateLink/qrcode" \
  -H "Authorization: Bearer <access_token>" \
  --output privateLink_qrcode.png
```

#### 8.2 QR-код для публичной ссылки (без авторизации)
```bash
curl -X GET "http://localhost:8000/publicLink/qrcode" \
  --output publicLink_qrcode.png
```

### 9. Обновление ссылки (для приватной ссылки)

**Запрос:**
```bash
curl -X PUT "http://localhost:8000/privateLink" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
        "original_url": "https://updated-example.com",
        "custom_alias": "privateLink",
        "category": "Updated",
        "expires_at": "2026-01-01T00:00:00",
        "is_public": false
      }'
```

### 10. Удаление ссылки (для приватной ссылки)

**Запрос:**
```bash
curl -X DELETE "http://localhost:8000/privateLink" \
  -H "Authorization: Bearer <access_token>"
```

**Пример ответа:**
```json
{
  "message": "Link deleted"
}
```

### 11. Редирект по короткому коду

#### Запрос для приватной ссылки
```bash
curl -L "http://localhost:8000/privateLink"
```

#### Запрос для публичной ссылки
```bash
curl -L "http://localhost:8000/publicLink"
```

> **Пояснение:** Редирект осуществляется без авторизации; сервер увеличивает счётчик редиректов и перенаправляет на оригинальный URL.

---

## Инструкция по запуску

Эта инструкция описывает, как запустить проект с использованием Docker и Docker Compose.

---

## Шаг 1: Клонирование репозитория

Клонируйте репозиторий с кодом проекта:

```bash
git clone <URL_репозитория>
cd <название_репозитория>
```

---

## Шаг 2: Настройка переменных окружения (опционально)

В файле `docker-compose.yml` заданы переменные окружения для всех сервисов:

- `DATABASE_URL` — адрес подключения к базе данных PostgreSQL;
- `REDIS_URL` — адрес подключения к Redis;
- `SECRET_KEY` — секретный ключ для JWT;
- `REFRESH_TOKEN_EXPIRE_DAYS` — срок действия refresh токена;
- `INACTIVE_DAYS_THRESHOLD` — порог неактивности ссылок.

При необходимости отредактируйте эти значения в файле `docker-compose.yml`.

---

## Шаг 3: Запуск контейнеров

Запустите контейнеры с помощью Docker Compose:

```bash
docker-compose up --build
```

Эта команда:

- Соберёт образы для веб-сервера (FastAPI) и фоновых задач (Celery worker и beat).
- Запустит контейнеры для PostgreSQL и Redis.
- Привяжет порт `80` внутри контейнера к порту `8000` на хосте.

---

## Шаг 4: Доступ к API

После успешного запуска контейнеров API будет доступен по адресу:

```
http://localhost:8000
```

Также вы можете открыть Swagger UI для интерактивной документации API.

---


## Дополнительная информация

- **Просмотр логов:**

Логи контейнеров можно просматривать командой:

```bash
docker-compose logs -f
```

- **Автоматическое создание базы данных:**

При использовании Docker Compose контейнер PostgreSQL создаёт базу данных автоматически на основе переменных окружения (например, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).

---

Эта инструкция поможет вам быстро развернуть и протестировать проект.


---

## Описание базы данных

В качестве основной базы данных используется **PostgreSQL**.  
Сервис использует ORM **SQLAlchemy** для управления таблицами и связями.

База данных состоит из двух основных таблиц:

- **`users`** — хранит информацию о зарегистрированных пользователях.
- **`links`** — хранит данные о сокращённых ссылках.

---

## Таблица `users`

| Поле             | Тип данных    | Описание                                 |
|------------------|---------------|------------------------------------------|
| **id**           | Integer (PK)  | Уникальный идентификатор пользователя    |
| **username**     | String        | Имя пользователя (уникальное)            |
| **hashed_password** | String     | Хэшированный пароль пользователя         |
| **created_at**   | DateTime      | Дата и время регистрации пользователя    |

Связи:
- Один пользователь может создавать множество ссылок (`one-to-many` с таблицей `links`).

---

## Таблица `links`

| Поле                | Тип данных    | Описание                                              |
|---------------------|---------------|-------------------------------------------------------|
| **id**              | Integer (PK)  | Уникальный идентификатор ссылки                       |
| **original_url**    | String        | Исходный (длинный) URL                                |
| **short_code**      | String        | Уникальный короткий код (алиас) ссылки                |
| **created_at**      | DateTime      | Дата и время создания ссылки                          |
| **expires_at**      | DateTime      | Время истечения ссылки (может быть NULL)              |
| **redirect_count**  | Integer       | Количество выполненных редиректов по ссылке           |
| **last_redirect_at**| DateTime      | Дата и время последнего редиректа (может быть NULL)   |
| **owner_id**        | Integer (FK)  | ID пользователя-создателя ссылки (может быть NULL для публичных ссылок) |
| **category**        | String        | Категория ссылки (необязательное поле)                |
| **is_public**       | Boolean       | Флаг публичности ссылки                               |

Связи:
- Каждая ссылка (если приватная) принадлежит одному пользователю (`many-to-one` с таблицей `users`).

---

## Дополнительная информация

- **Индексы и ограничения**: 
  - Поле `username` в таблице пользователей имеет ограничение уникальности (unique).
  - Поле `short_code` в таблице ссылок также имеет ограничение уникальности, обеспечивая уникальность короткого адреса.
- **Кэширование**:
  - Для ускорения работы сервиса используется **Redis** для кэширования наиболее часто используемых ссылок и редиректов.
- **Автоматическая очистка данных**:
  - **Celery** используется для автоматической очистки просроченных и неактивных ссылок.

Эта структура базы данных обеспечивает эффективное и надёжное хранение данных, необходимое для работы сервиса сокращения ссылок.




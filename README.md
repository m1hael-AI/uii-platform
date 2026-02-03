# AI University - Образовательная платформа

## Обзор проекта

**AI University** — образовательная платформа с проактивными AI-агентами, которые выступают персональными наставниками для пользователей.

### Ключевые возможности:
- Авторизация через Telegram Widget + JWT токены
- Множественные AI-агенты с редактируемыми системными промптами
- Библиотека вебинаров с RAG-чатом (ответы по транскрипту видео)
- Проактивная система: Summarizer анализирует диалоги, Executor отправляет умные напоминания
- Админ-панель для управления агентами, промптами и контентом

---

## Архитектура

### Стек технологий:

**Frontend:**
- Next.js 14+ (App Router)
- Tailwind CSS (светлая тема)
- TypeScript

**Backend:**
- FastAPI (Python)
- SQLModel (SQLAlchemy + Pydantic ORM)
- PostgreSQL
- WebSockets для AI-стриминга

**Интеграции:**
- aiogram 3.x (Telegram Bot через webhook)
- AsyncOpenAI (асинхронные запросы к LLM)
- aioboto3 (S3-совместимое хранилище)

---

## Структура проекта

```
/
├── docker-compose.yml       # Docker конфигурация для VPS
├── .env.example             # Пример переменных окружения
├── backend/
│   ├── main.py              # FastAPI приложение + webhook endpoint
│   ├── config.py            # Конфигурация из .env
│   ├── models.py            # SQLModel схемы БД (8 таблиц)
│   ├── database.py          # Инициализация подключения к БД
│   ├── requirements.txt     # Python зависимости
│   ├── Dockerfile           # Docker образ backend
│   ├── bot/
│   │   ├── loader.py        # Инициализация Bot/Dispatcher
│   │   └── router.py        # Обработчики команд Telegram
│   └── services/
│       ├── openai_service.py    # AsyncOpenAI для AI-агентов
│       └── storage_service.py   # aioboto3 для S3 хранилища
└── frontend/
    ├── src/app/             # Next.js App Router
    ├── package.json         # Node.js зависимости
    └── Dockerfile           # Docker образ frontend
```

---

## База данных (PostgreSQL)

### Таблицы:

1. **users** - Пользователи (tg_id, role, is_onboarded, timezone)
2. **user_memories** - Нарративное резюме пользователя для агентов
3. **agents** - AI-агенты (slug, name, system_prompt, avatar_url)
4. **system_configs** - Key-Value хранилище глобальных промптов
5. **pending_actions** - Очередь проактивных действий
6. **webinars** - Вебинары (video_url, transcript_context для RAG)
7. **chat_sessions** - Сессии чата пользователь-агент
8. **messages** - История сообщений

---

## Запуск

### В Replit:
```bash
# Frontend (порт 5000)
cd frontend && npm run dev

# Backend (порт 8000)
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
```

### На VPS (Docker):
```bash
docker-compose up -d
```

---

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - Ключ OpenAI API
- `TELEGRAM_BOT_TOKEN` - Токен Telegram бота
- `S3_ENDPOINT_URL` - Endpoint S3-хранилища (Supabase/MinIO/AWS)
- `JWT_SECRET` - Секрет для JWT токенов

---

## Vendor-Agnostic подход

Проект спроектирован для лёгкой миграции:

1. **База данных**: Стандартный PostgreSQL connection string через SQLModel
2. **Хранилище**: S3-совместимый протокол через aioboto3
3. **OpenAI**: Стандартный SDK с AsyncOpenAI

Для миграции достаточно изменить переменные в `.env`.

---

## Асинхронные сервисы

### OpenAI Service (services/openai_service.py)
- `generate_chat_response()` - Генерация ответа без стриминга
- `stream_chat_response()` - Генерация со стримингом для WebSocket
- `summarize_conversation()` - Анализ диалога для Summarizer

### Storage Service (services/storage_service.py)
- `upload_file()` - Загрузка файла в S3
- `download_file()` - Скачивание файла
- `delete_file()` - Удаление файла
- `generate_presigned_url()` - Генерация временного URL

---

## Последние изменения

- **2026-01-20**: UI улучшения
  - Личный кабинет (/platform/profile): профиль, статистика, настройки уведомлений
  - Левая панель: частичное сворачивание (только иконки)
  - Чаты сортируются по времени последнего сообщения
  - Система уведомлений: колокольчик, badge непрочитанных, dropdown
  - Чат вебинара: несворачиваемый, увеличенный размер
  - Личный помощник: в списке чатов + floating виджет (синхронизированы)

- **2026-01-20**: Telegram-стиль UI
  - Левая панель: навигация + чаты с AI-личностями (Аналитик, Креатив, Ментор, Практик)
  - Отдельные страницы чатов для каждого агента (/platform/chat/[agentId])
  - RAG-чат на странице вебинара (вопросы по конкретному видео)

- **2026-01-19**: Инициализация проекта, создана базовая структура
  - docker-compose.yml для VPS деплоя
  - Backend: FastAPI + SQLModel + aiogram webhook
  - Frontend: Next.js 14 + Tailwind CSS (светлая тема)
  - Полная схема БД (8 таблиц)
  - Асинхронные сервисы: OpenAI (AsyncOpenAI) и Storage (aioboto3)
  - Инициализация БД при старте приложения

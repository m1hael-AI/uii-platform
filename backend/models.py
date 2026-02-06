"""
Модели базы данных AI University.
Используем SQLModel (SQLAlchemy + Pydantic) для vendor-agnostic подхода.
Все модели работают с любым PostgreSQL через стандартный connection string.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import JSON, Column, BigInteger, Text
from enum import Enum


# === ENUMS ===

class UserRole(str, Enum):
    """Роли пользователей в системе"""
    ADMIN = "admin"
    USER = "user"


class MessageRole(str, Enum):
    """Роли в чате (кто отправил сообщение)"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# === ОСНОВНЫЕ МОДЕЛИ ===

class User(SQLModel, table=True):
    """
    Пользователь системы.
    Авторизация через Telegram Widget -> JWT.
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    # tg_id теперь опционален, так как вход может быть через email
    tg_id: Optional[int] = Field(
        default=None, 
        sa_column=Column(BigInteger, unique=True, index=True),
        description="Уникальный Telegram ID пользователя"
    )
    
    # Данные из Telegram
    tg_username: Optional[str] = Field(default=None, description="Username в Telegram")
    tg_first_name: Optional[str] = Field(default=None, description="Имя пользователя")
    tg_last_name: Optional[str] = Field(default=None, description="Фамилия пользователя")
    tg_photo_url: Optional[str] = Field(default=None, description="URL аватара из Telegram")
    
    # Личные данные (Log/Pass)
    phone: Optional[str] = Field(default=None, description="Номер телефона")
    email: Optional[str] = Field(default=None, index=True, description="Email для входа")
    hashed_password: Optional[str] = Field(default=None, description="Хэш пароля (если вход по email)")
    
    # Маркетинг (UTM метки)
    utm_source: Optional[str] = Field(default=None)
    utm_medium: Optional[str] = Field(default=None)
    utm_campaign: Optional[str] = Field(default=None)
    utm_content: Optional[str] = Field(default=None)
    
    # Ответы на квиз (храним как JSON)
    quiz_answers: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    
    # Роль и статус
    role: UserRole = Field(default=UserRole.USER, description="Роль: admin или user")
    is_onboarded: bool = Field(default=False, description="Прошёл ли пользователь онбординг (квиз)")
    is_active: bool = Field(default=True, description="Активен ли аккаунт")
    
    # Временная зона для тихих часов
    timezone: str = Field(default="Europe/Moscow", description="Часовой пояс пользователя")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: Optional[datetime] = Field(default=None, description="Последняя активность для проактивности")
    
    # Relationships
    memory: Optional["UserMemory"] = Relationship(back_populates="user")
    chat_sessions: List["ChatSession"] = Relationship(back_populates="user")
    pending_actions: List["PendingAction"] = Relationship(back_populates="user")
    actions: List["UserAction"] = Relationship(back_populates="user")
    webinar_signups: List["WebinarSignup"] = Relationship(back_populates="user")


class UserAction(SQLModel, table=True):
    """
    Лог действий пользователя (Audit Log).
    Пишем только важные бизнес-события: регистрация, запись на вебинар и т.д.
    """
    __tablename__ = "user_actions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    action: str = Field(description="Тип действия (registration, webinar_signup, etc)")
    payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON), description="Доп. данные (например ID вебинара)")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: Optional[User] = Relationship(back_populates="actions")


class UserMemory(SQLModel, table=True):
    """
    Память о пользователе (нарративное резюме).
    Доступна read-only для ВСЕХ агентов.
    Обновляется Summarizer'ом после каждого диалога.
    """
    __tablename__ = "user_memories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    
    # Нарративное резюме о пользователе
    # Содержит: интересы, цели, прогресс, особенности общения
    narrative_summary: str = Field(default="", description="Текстовое резюме о пользователе для агентов")
    
    # Когда последний раз обновлялось резюме
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    user: Optional[User] = Relationship(back_populates="memory")


class Agent(SQLModel, table=True):
    """
    AI-агент (персонаж) системы.
    Каждый агент имеет свой system prompt и роль.
    Редактируется через админ-панель.
    """
    __tablename__ = "agents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True, description="Уникальный идентификатор агента (personal-assistant, curator, etc)")
    name: str = Field(description="Отображаемое имя агента")
    
    # Аватар агента (URL к изображению в S3)
    avatar_url: Optional[str] = Field(default=None, description="URL аватара агента")
    
    # System prompt агента (редактируется в админке)
    system_prompt: str = Field(default="", description="Системный промпт агента")
    
    # Приветственное сообщение
    greeting_message: Optional[str] = Field(default=None, description="Приветственное сообщение для начала диалога")
    
    # Описание для UI
    description: Optional[str] = Field(default=None, description="Краткое описание агента для пользователей")
    
    # Активен ли агент
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    chat_sessions: List["ChatSession"] = Relationship(back_populates="agent")
    pending_actions: List["PendingAction"] = Relationship(back_populates="agent")


class SystemConfig(SQLModel, table=True):
    """
    Системные настройки (Key-Value store).
    Используется для хранения глобальных промптов.
    Например: judge_prompt для Summarizer.
    """
    __tablename__ = "system_configs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, description="Ключ настройки (judge_prompt, etc)")
    value: str = Field(default="", description="Значение настройки (текст промпта)")
    description: Optional[str] = Field(default=None, description="Описание настройки для админки")
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PendingAction(SQLModel, table=True):
    """
    Отложенное действие для проактивности.
    Создаётся Summarizer'ом, выполняется Executor'ом (cron).
    Kill Switch: удаляется при активности пользователя с этим агентом.
    """
    __tablename__ = "pending_actions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agent_slug: str = Field(foreign_key="agents.slug", index=True)
    
    # Контекст темы для начала разговора
    topic_context: str = Field(description="Контекст темы, о которой агент должен начать разговор")
    
    # Приоритет (для сортировки в очереди)
    priority: int = Field(default=0, description="Приоритет действия (выше = важнее)")
    
    # Статус выполнения
    status: str = Field(default="pending", description="Статус: pending, sent, failed")
    
    # Когда создано и отправлено
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = Field(default=None, description="Когда было отправлено проактивное сообщение")
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="pending_actions")
    agent: Optional[Agent] = Relationship(back_populates="pending_actions")





class ProactivitySettings(SQLModel, table=True):
    """
    Настройки проактивности системы.
    Редактируется через админ-панель.
    Должна быть только одна запись (singleton).
    """
    __tablename__ = "proactivity_settings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # === OpenAI Settings ===
    model: str = Field(default="gpt-4.1-mini", description="Модель OpenAI для генерации")
    temperature: float = Field(default=0.7, description="Temperature для генерации")
    max_tokens: int = Field(default=2000, description="Максимум токенов в ответе")
    
    # === Scheduler Settings ===
    enabled: bool = Field(default=True, description="Включена ли проактивность")
    cron_expression: str = Field(default="0 */1 * * *", description="Cron выражение для планировщика (каждый час)")
    quiet_hours_start: str = Field(default="22:00", description="Начало тихих часов (HH:MM)")
    quiet_hours_end: str = Field(default="10:00", description="Конец тихих часов (HH:MM)")
    
    # === Limits ===
    max_messages_per_day_agents: int = Field(default=3, description="Макс. сообщений в день для всех агентов вместе")
    max_messages_per_day_assistant: int = Field(default=3, description="Макс. сообщений в день для AI Помощника отдельно")
    
    # === Summarizer Settings ===
    summarizer_check_interval: int = Field(default=2, description="Интервал проверки Cron (минуты)")
    summarizer_idle_threshold: int = Field(default=5, description="Диалог завершён через N минут молчания")
    
    # === Context Compression Settings (Вечный диалог) ===
    # Делаем Optional для миграции, но с дефолтами для логики
    context_soft_limit: Optional[int] = Field(default=350000, description="Жесткий лимит токенов (max_tokens) для срабатывания сжатия")
    context_threshold: Optional[float] = Field(default=0.9, description="Порог срабатывания сжатия (0.9 = 90% от лимита)")
    context_compression_keep_last: Optional[int] = Field(default=20, description="Сколько последних сообщений оставлять при сжатии")
    
    # === Rate Limiter ===
    rate_limit_per_minute: int = Field(default=15, description="Лимит сообщений в минуту от пользователя")
    
    
    # === Prompts ===
    agent_memory_prompt: str = Field(
        default="""Проанализируй ВЕСЬ диалог и извлеки важную информацию о пользователе.

=== ПОЛНАЯ ИСТОРИЯ ДИАЛОГА ===
{full_chat_history}

=== ТЕКУЩАЯ ПАМЯТЬ О ПОЛЬЗОВАТЕЛЕ (для этого агента) ===
{current_memory}

=== ГЛОБАЛЬНАЯ БИОГРАФИЯ ===
{user_profile}

=== ЗАДАЧИ ===
1. ИЗВЛЕКИ новые важные факты о пользователе из диалога:
   - Интересы, цели, навыки
   - Прогресс в обучении
   - Проблемы, с которыми столкнулся
   - Планы на будущее

2. ДОБАВЬ эти факты к текущей памяти (НЕ заменяй, а ДОПОЛНИ)

3. Определи, нужно ли создать проактивную задачу:
   - Есть ли незавершённые темы?
   - Проявил ли пользователь интерес, но не получил полного ответа?
   - Стоит ли напомнить о чём-то?

Верни ТОЛЬКО валидный JSON:
{{
  "memory_update": "Обновлённая память с новыми фактами, добавленными к старым",
  "create_task": true,
  "topic": "Конкретная тема для проактивного сообщения"
}}

Если задача не нужна:
{{
  "memory_update": "Обновлённая память...",
  "create_task": false
}}""",
        description="Промпт для извлечения памяти агентов"
    )
    
    assistant_memory_prompt: str = Field(
        default="""Проанализируй ВЕСЬ диалог и извлеки важную информацию о пользователе.

=== ПОЛНАЯ ИСТОРИЯ ДИАЛОГА ===
{full_chat_history}

=== ТЕКУЩАЯ ПАМЯТЬ О ПОЛЬЗОВАТЕЛЕ (для AI Помощника) ===
{current_memory}

=== ГЛОБАЛЬНАЯ БИОГРАФИЯ ===
{user_profile}

=== ВСЕ ЛОКАЛЬНЫЕ ПАМЯТИ ДРУГИХ АГЕНТОВ ===
{all_agent_memories}

=== ЗАДАЧИ ===
1. ИЗВЛЕКИ новые важные факты о пользователе из диалога

2. ДОБАВЬ их к текущей памяти AI Помощника (НЕ заменяй, а ДОПОЛНИ)

3. ОБНОВИ глобальную биографию пользователя, объединив:
   - Локальную память AI Помощника
   - Все локальные памяти других агентов
   - Создай единый профиль пользователя

4. Определи, нужно ли создать проактивную задачу

Верни ТОЛЬКО валидный JSON:
{{
  "memory_update": "Обновлённая локальная память AI Помощника",
  "global_profile_update": "Обновлённая глобальная биография пользователя",
  "create_task": true,
  "topic": "Тема для проактивного сообщения"
}}

Если задача не нужна:
{{
  "memory_update": "...",
  "global_profile_update": "...",
  "create_task": false
}}""",
        description="Промпт для AI Помощника (обновляет глобальный профиль)"
    )
    
    # Timestamps
    updated_at: datetime = Field(default_factory=datetime.utcnow)



class WebinarSchedule(SQLModel, table=True):
    """
    Расписание предстоящих вебинаров.
    """
    __tablename__ = "webinar_schedules"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(description="Название вебинара")
    description: Optional[str] = Field(default=None, description="Описание вебинара")
    
    # Ссылка для подключения (Zoom/Meet) - для кнопки входа
    connection_link: Optional[str] = Field(default=None, description="Ссылка для подключения (Zoom/Meet)")
    
    # Превью
    thumbnail_url: Optional[str] = Field(default=None, description="URL превью вебинара")
    speaker_name: Optional[str] = Field(default=None, description="Имя спикера")
    
    # Статус
    is_published: bool = Field(default=True, description="Опубликован ли вебинар")
    
    # Расписание
    scheduled_at: datetime = Field(description="Дата и время начала (UTC)")
    duration_minutes: int = Field(default=60, description="Длительность (мин)")
    
    # Напоминания
    reminder_1h_sent: bool = Field(default=False, description="Отправлено уведомление за 1 час (глобально)")
    reminder_15m_sent: bool = Field(default=False, description="Отправлено уведомление за 15 минут (глобально)")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    signups: List["WebinarSignup"] = Relationship(back_populates="schedule")
    chat_sessions: List["ChatSession"] = Relationship(back_populates="schedule")


class WebinarLibrary(SQLModel, table=True):
    """
    Библиотека прошедших вебинаров (записи).
    """
    __tablename__ = "webinar_libraries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(description="Название вебинара")
    description: Optional[str] = Field(default=None, description="Описание вебинара")
    
    # URL видео (iframe src)
    video_url: str = Field(description="URL видео/трансляции (плеер)")
    
    # Превью
    thumbnail_url: Optional[str] = Field(default=None, description="URL превью вебинара")
    speaker_name: Optional[str] = Field(default=None, description="Имя спикера")
    
    # RAG
    transcript_context: str = Field(default="", description="Текстовый транскрипт вебинара для RAG")
    
    # Статус
    is_published: bool = Field(default=True, description="Опубликован ли вебинар")
    
    # Когда был проведен (для сортировки в библиотеке)
    conducted_at: datetime = Field(default_factory=datetime.utcnow, description="Дата проведения (UTC)")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    chat_sessions: List["ChatSession"] = Relationship(back_populates="library")


class WebinarSignup(SQLModel, table=True):
    """
    Таблица записей на вебинары (для рассылок и оптимизации).
    """
    __tablename__ = "webinar_signups"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    schedule_id: int = Field(foreign_key="webinar_schedules.id", index=True)
    
    # Статус доставки уведомлений персонально этому пользователю
    reminder_1h_sent: bool = Field(default=False, description="Отправлено ли личное напоминание за 1 час")
    reminder_start_sent: bool = Field(default=False, description="Отправлено ли личное напоминание о старте")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="webinar_signups")
    schedule: Optional[WebinarSchedule] = Relationship(back_populates="signups")


class ChatSession(SQLModel, table=True):
    """
    Сессия чата между пользователем и агентом.
    Может быть привязана к предстоящему вебинару или записи в библиотеке.
    """
    __tablename__ = "chat_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agent_slug: str = Field(foreign_key="agents.slug", index=True)
    
    # Опциональная привязка к расписанию или библиотеке (для RAG)
    schedule_id: Optional[int] = Field(default=None, foreign_key="webinar_schedules.id", index=True)
    library_id: Optional[int] = Field(default=None, foreign_key="webinar_libraries.id", index=True)
    
    # Активна ли сессия
    is_active: bool = Field(default=True)
    
    # Когда пользователь последний раз читал сообщения в этой сессии
    last_read_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = Field(default=None, description="Время последнего сообщения (для debounce)")
    summarized_at: Optional[datetime] = Field(default=None, description="Время последней суммаризации (для проактивности)")
    
    # Локальная суммаризация для агента (проактивность)
    local_summary: Optional[str] = Field(default=None, description="Локальная суммаризация диалога с этим агентом")
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="chat_sessions")
    agent: Optional[Agent] = Relationship(back_populates="chat_sessions")
    schedule: Optional[WebinarSchedule] = Relationship(back_populates="chat_sessions")
    library: Optional[WebinarLibrary] = Relationship(back_populates="chat_sessions")
    messages: List["Message"] = Relationship(back_populates="session")


class Message(SQLModel, table=True):
    """
    Сообщение в чате.
    Хранит историю диалога для контекста LLM.
    """
    __tablename__ = "messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chat_sessions.id", index=True)
    
    # Роль отправителя (user/assistant/system)
    role: MessageRole = Field(description="Кто отправил сообщение")
    
    # Текст сообщения
    content: str = Field(description="Текст сообщения")
    
    # Метаданные (например, tokens used, model)
    message_metadata: Optional[str] = Field(default=None, description="JSON с метаданными сообщения")
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    session: Optional[ChatSession] = Relationship(back_populates="messages")


class MagicLinkToken(SQLModel, table=True):
    """
    Токен для одноразовой ссылки входа (Magic Link).
    При генерации нового, старые отзываются.
    """
    __tablename__ = "magic_link_tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    token: str = Field(unique=True, index=True, description="Уникальный токен ссылки")
    
    expires_at: datetime = Field(description="Срок действия ссылки")
    is_used: bool = Field(default=False, description="Использована ли ссылка")
    is_revoked: bool = Field(default=False, description="Отозвана ли ссылка (сгенерирована новая)")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PasswordResetToken(SQLModel, table=True):
    """
    Токены для сброса пароля через Telegram.
    Код отправляется в бота, пользователь вводит на сайте.
    """
    __tablename__ = "password_reset_tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    code: str = Field(description="6-значный код для подтверждения")
    attempts: int = Field(default=0, description="Количество попыток ввода кода")
    max_attempts: int = Field(default=5, description="Максимум попыток")
    
    ip_address: Optional[str] = Field(default=None, description="IP адрес запросившего")
    
    is_used: bool = Field(default=False, description="Использован ли код")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(description="Время истечения кода (10 минут)")


# === ВСПОМОГАТЕЛЬНЫЕ МОДЕЛИ (не для БД) ===

class TokenPayload(SQLModel):
    """Payload JWT токена (не сохраняется в БД)"""
    sub: int  # user_id
    tg_id: int
    role: UserRole
    exp: datetime


class TelegramAuthData(SQLModel):
    """Данные авторизации из Telegram Widget (не сохраняется в БД)"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

# === LOGGING Models ===

class LLMAudit(SQLModel, table=True):
    """
    Аудит всех запросов к LLM (OpenAI).
    Хранит полную историю запросов и ответов для отладки.
    Записи старше 7 дней должны очищаться (поле request/response) или удаляться полностью.
    """
    __tablename__ = "llm_audit"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    agent_slug: str = Field(index=True)
    model: str
    
    # Stats
    input_tokens: int = 0
    cached_tokens: int = 0  # New field for Prompt Caching
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    
    # Content (Full Log) - большие тексты
    request_json: str = Field(sa_column=Column(Text))
    response_json: str = Field(sa_column=Column(Text))
    
    # Metadata
    status: str = "success" # success, error
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


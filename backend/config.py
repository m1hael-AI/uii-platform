"""
Конфигурация приложения AI University.
Все секреты загружаются из переменных окружения (.env файл).
Архитектура vendor-agnostic: легко мигрировать на любой сервер.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Настройки приложения.
    Все значения берутся из переменных окружения или .env файла.
    """
    
    # === База данных (PostgreSQL) ===
    # Стандартный connection string, работает с любым PostgreSQL
    # Supabase, self-hosted, AWS RDS - просто меняем строку подключения
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_university")
    
    # === Redis ===
    redis_url: Optional[str] = os.getenv("REDIS_URL")
    
    # === OpenAI API ===
    # Стандартный API ключ, без vendor lock-in
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # === S3-совместимое хранилище ===
    # Работает через aioboto3, совместимо с:
    # - Supabase Storage (S3-compatible)
    # - MinIO (self-hosted)
    # - AWS S3
    # - Beget S3
    # Для миграции достаточно сменить endpoint_url
    s3_endpoint_url: Optional[str] = os.getenv("S3_ENDPOINT_URL")
    s3_access_key: Optional[str] = os.getenv("S3_ACCESS_KEY")
    s3_secret_key: Optional[str] = os.getenv("S3_SECRET_KEY")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "ai-university")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")
    
    # === Telegram Bot ===
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_bot_username: Optional[str] = os.getenv("TELEGRAM_BOT_USERNAME")
    telegram_webhook_url: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    
    # === JWT Авторизация ===
    # Кастомная реализация, без внешних провайдеров
    jwt_secret: str = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_hours: int = int(os.getenv("JWT_EXPIRE_HOURS", "168"))  # 7 дней по умолчанию
    
    # === Настройки приложения ===
    app_name: str = "AI University"
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # === CORS настройки ===
    # Разрешённые origins для фронтенда
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5000",
        "https://*.replit.dev",
    ]
    
    # === Проактивность (Executor) ===
    # Тихие часы: не отправляем сообщения с 22:00 до 10:00
    silent_hours_start: int = 22
    silent_hours_end: int = 10
    # Максимальная частота проактивных сообщений Personal Assistant
    proactive_interval_hours: int = 24
    # Debounce для Summarizer (минуты после последнего сообщения)
    summarizer_debounce_minutes: int = 15
    
    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Кэшированное получение настроек.
    Настройки загружаются один раз при старте приложения.
    """
    return Settings()


# Глобальный экземпляр настроек для удобства импорта
settings = get_settings()

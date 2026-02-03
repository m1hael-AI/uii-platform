"""
Инициализация Telegram бота и Dispatcher.
Здесь создаются основные объекты aiogram:
- Bot: для отправки сообщений
- Dispatcher: для обработки входящих update'ов
"""

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import sys
import os

# Добавляем родительскую директорию в path для импорта config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


# === ИНИЦИАЛИЗАЦИЯ БОТА ===
# Создаём экземпляр бота с настройками по умолчанию
bot = Bot(
    token=settings.telegram_bot_token or "placeholder_token",
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML  # HTML разметка по умолчанию
    )
)


# === STORAGE ===
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

storage = MemoryStorage()
if settings.redis_url:
    try:
        storage = RedisStorage.from_url(settings.redis_url)
        # Check connection implicitly or just hope it works?
        # aiogram will try to connect when used.
    except Exception as e:
        print(f"Redis connection failed, falling back to MemoryStorage: {e}")

# === DISPATCHER ===
# Dispatcher управляет обработкой входящих update'ов
dp = Dispatcher(storage=storage)


# Подключаем роутеры с обработчиками
from bot.router import router as main_router
dp.include_router(main_router)

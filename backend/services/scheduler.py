"""
Планировщик задач для проактивности AI University.
Использует APScheduler для запуска Cron задач.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from loguru import logger

from config import settings
from services.summarizer import check_idle_conversations
from services.proactive_scheduler import process_pending_actions
from services.webinar_notifier import check_webinar_reminders


# Создаём engine для scheduler (отдельный от FastAPI)
# Заменяем postgresql:// на postgresql+asyncpg:// для async драйвера
database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

scheduler_engine = create_async_engine(
    database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    scheduler_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Создаём scheduler
scheduler = AsyncIOScheduler()


async def summarizer_job():
    """Задача суммаризатора: проверяет застывшие чаты"""
    async with AsyncSessionLocal() as db:
        try:
            await check_idle_conversations(db)
        except Exception as e:
            logger.error(f"❌ Ошибка в summarizer_job: {e}")


async def proactive_job():
    """Задача проактивности: обрабатывает pending задачи"""
    async with AsyncSessionLocal() as db:
        try:
            await process_pending_actions(db)
        except Exception as e:
            logger.error(f"❌ Ошибка в proactive_job: {e}")


async def webinar_reminders_job():
    """Задача проверки напоминаний о вебинарах"""
    async with AsyncSessionLocal() as db:
        try:
            await check_webinar_reminders(db)
        except Exception as e:
            logger.error(f"❌ Ошибка в webinar_reminders_job: {e}")


def start_scheduler():
    """Запуск планировщика"""
    # Добавляем задачу суммаризатора (каждые 2 минуты)
    scheduler.add_job(
        summarizer_job,
        trigger=IntervalTrigger(minutes=2),
        id="summarizer_check",
        name="Проверка застывших чатов",
        replace_existing=True,
    )

    # Добавляем задачу напоминаний о вебинарах (каждую минуту)
    scheduler.add_job(
        webinar_reminders_job,
        trigger=IntervalTrigger(minutes=1),
        id="webinar_reminders",
        name="Рассылка напоминаний о вебинарах",
        replace_existing=True,
    )
    
    # Добавляем задачу проактивности (каждый час)
    scheduler.add_job(
        proactive_job,
        trigger=IntervalTrigger(hours=1),
        id="proactive_check",
        name="Обработка проактивных задач",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("✅ Планировщик запущен")


def stop_scheduler():
    """Остановка планировщика"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 Планировщик остановлен")

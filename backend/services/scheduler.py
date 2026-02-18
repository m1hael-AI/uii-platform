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
from services.audit_service import cleanup_old_logs
from services.news.jobs import harvest_news_nightly, generate_articles_periodic
from models import NewsSettings
from sqlalchemy import select
from apscheduler.triggers.cron import CronTrigger



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

async def cleanup_job():
    """Задача очистки старых логов"""
    try:
        await cleanup_old_logs(7)
    except Exception as e:
        logger.error(f"❌ Ошибка в cleanup_job: {e}")



async def start_scheduler():
    """Запуск планировщика"""
    # 1. Сначала загружаем настройки из БД
    harvester_cron = "0 2 * * *"  # Default 2:00 AM
    generator_cron = "*/15 * * * *" # Default every 15 mins
    harvester_enabled = True
    generator_enabled = True

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(NewsSettings).limit(1)
            result = await db.execute(stmt)
            settings = result.scalar_one_or_none()
            
            if settings:
                harvester_cron = settings.harvester_cron
                generator_cron = settings.generator_cron
                harvester_enabled = settings.harvester_enabled
                generator_enabled = settings.generator_enabled
                logger.info(f"📅 Loaded News Schedule: Harvester='{harvester_cron}', Generator='{generator_cron}'")
            else:
                logger.warning("⚠️ NewsSettings not found, using defaults.")
                
    except Exception as e:
        logger.error(f"❌ Failed to load schedule settings: {e}")

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
    
    # Добавляем задачу проактивности (каждую 1 минуту для теста)
    scheduler.add_job(
        proactive_job,
        trigger=IntervalTrigger(minutes=1),
        id="proactive_check",
        name="Обработка проактивных задач",
        replace_existing=True,
    )
    
    # Добавляем задачу очистки логов (каждые 24 часа)
    scheduler.add_job(
        cleanup_job,
        trigger=IntervalTrigger(hours=24),
        id="cleanup_logs",
        name="Очистка старых логов LLM",
        replace_existing=True,
    )
    

    
    # --- AI News Jobs ---
    
    # 1. Ночной сборщик новостей
    if harvester_enabled:
        try:
            scheduler.add_job(
                harvest_news_nightly,
                trigger=CronTrigger.from_crontab(harvester_cron),
                id="news_harvester",
                name="Сбор AI новостей (Harvester)",
                replace_existing=True
            )
        except Exception as e:
            logger.error(f"❌ Invalid Harvester Cron '{harvester_cron}': {e}")
    else:
        logger.info("🔕 News Harvester is DISABLED")
    
    # 2. Генератор статей
    if generator_enabled:
        try:
            scheduler.add_job(
                generate_articles_periodic,
                trigger=CronTrigger.from_crontab(generator_cron),
                id="news_generator",
                name="Генерация статей (Writer)",
                replace_existing=True
            )
        except Exception as e:
            logger.error(f"❌ Invalid Generator Cron '{generator_cron}': {e}")
    else:
        logger.info("🔕 News Generator is DISABLED")
    
    scheduler.start()
    logger.info("✅ Планировщик запущен")


def stop_scheduler():
    """Остановка планировщика"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 Планировщик остановлен")

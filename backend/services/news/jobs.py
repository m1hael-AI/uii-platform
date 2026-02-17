import logging
import asyncio
from sqlalchemy import select
from loguru import logger

from database import async_session_factory
from services.news.manager import NewsManager
from services.news.perplexity import PerplexityClient
from models import NewsItem, NewsStatus

logger = logging.getLogger(__name__)

async def harvest_news_nightly():
    """
    Задача для крона (раз в сутки).
    Ищет топ новостей через Harvester и сохраняет в БД.
    """
    logger.info("🌙 Starting Nightly News Harvester Job...")
    async with async_session_factory() as db:
        try:
            manager = NewsManager(db)
            client = PerplexityClient()
            
            # 1. Fetch
            logger.info("📡 Fetching top AI news...")
            news_items = await client.search_news()
            
            if not news_items:
                logger.warning("⚠️ No news found.")
                return

            # 2. Ingest
            count = await manager.add_news_items(news_items)
            logger.info(f"🎉 Harvest Complete. Added {count} items.")
            
        except Exception as e:
            logger.error(f"❌ Harvester Job Failed: {e}")


async def generate_articles_periodic():
    """
    Задача для интервала (раз в 15 мин).
    Берет PENDING новости и генерирует статьи.
    """
    logger.info("🏭 Starting Article Generator Job...")
    async with async_session_factory() as db:
        try:
            manager = NewsManager(db)
            
            # 1. Find Pending
            stmt = select(NewsItem).where(NewsItem.status == NewsStatus.PENDING).limit(5)
            result = await db.execute(stmt)
            pending_items = result.scalars().all()
            
            if not pending_items:
                # logger.info("💤 No pending items.") # Slience log to avoid spam
                return

            logger.info(f"⚡ Found {len(pending_items)} pending items.")
            
            # 2. Process
            for item in pending_items:
                try:
                    article = await manager.trigger_generation(item.id)
                    if article:
                        logger.info(f"   ✅ Generated: {article.title}")
                    else:
                        logger.warning(f"   ⚠️ Failed to generate: {item.title}")
                    
                    # Small delay to be nice to API
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"   ❌ Error processing item {item.id}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Generator Job Failed: {e}")

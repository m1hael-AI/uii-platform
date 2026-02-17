import asyncio
import sys
import os
import logging
from loguru import logger

# Add parent dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import async_session_factory
from services.news.manager import NewsManager
from services.news.perplexity import PerplexityClient

# Configure Logging
logger.add("logs/harvester.log", rotation="1 MB", retention="7 days", level="INFO")

async def main():
    logger.info("🌙 Starting Nightly News Harvester...")
    
    try:
        async with async_session_factory() as session:
            manager = NewsManager(session)
            client = PerplexityClient()
            
            # 1. Fetch Top News (Default behavior when query is None)
            logger.info("📡 Fetching top AI news from Perplexity...")
            news_items = await client.search_news()
            
            if not news_items:
                logger.warning("⚠️ No news found. Check API or prompts.")
                return

            logger.info(f"✅ Found {len(news_items)} items. Examples:")
            for item in news_items[:3]:
                logger.info(f"   - {item.title}")

            # 2. Ingest (Deduplication happens here)
            logger.info("💾 Ingesting into Database...")
            added_count = await manager.add_news_items(news_items)
            
            logger.info(f"🎉 Harvester Complete. Added {added_count} new items.")
            
    except Exception as e:
        logger.error(f"❌ Harvester Critical Failure: {e}")
        # In a real worker, we might want to alert Sentry/Telegram here

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

import asyncio
import sys
import os
import logging
from loguru import logger
from sqlalchemy import select

# Add parent dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import async_session_factory
from models import NewsItem, NewsStatus
from services.news.manager import NewsManager

# Configure Logging
logger.add("logs/generator.log", rotation="1 MB", retention="7 days", level="INFO")

async def main():
    logger.info("🏭 Starting Article Generator Worker...")
    
    try:
        async with async_session_factory() as session:
            manager = NewsManager(session)
            
            # 1. Find PENDING items
            stmt = select(NewsItem).where(NewsItem.status == NewsStatus.PENDING).limit(10)
            result = await session.execute(stmt)
            pending_items = result.scalars().all()
            
            if not pending_items:
                logger.info("💤 No pending items to process.")
                return

            logger.info(f"⚡ Found {len(pending_items)} pending items. Starting generation...")
            
            # 2. Process each item
            for item in pending_items:
                logger.info(f"   📝 Generating article for: '{item.title}' (ID: {item.id})")
                try:
                    article = await manager.trigger_generation(item.id)
                    if article:
                        logger.info(f"      ✅ Success! Length: {len(article.content)}")
                    else:
                        logger.warning(f"      ⚠️ Generation returned None (Status: {item.status})")
                        
                    # Sleep to respect rate limits if needed (though manager handles retries)
                    await asyncio.sleep(2) 
                    
                except Exception as e:
                    logger.error(f"      ❌ Failed to trigger generation: {e}")

            logger.info("🎉 Generator Worker Cycle Complete.")
            
    except Exception as e:
        logger.error(f"❌ Generator Critical Failure: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

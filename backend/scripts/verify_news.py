import asyncio
import sys
import os
import logging
from loguru import logger

# Add parent dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import async_engine, async_session_factory
from services.news.manager import NewsManager
from services.news.perplexity import PerplexityClient

async def main():
    logger.info("🚀 Starting News System Verification...")
    
    # 1. Check Prompts
    logger.info("1️⃣ Checking Prompts Loading...")
    client = PerplexityClient()
    if not client.prompts:
        logger.error("❌ Failed to load prompts from default_prompts.yaml")
        return
    logger.info(f"✅ Prompts loaded. Keys: {list(client.prompts.keys())}")
    
    # 2. Check Database & Manager
    logger.info("2️⃣ Checking Database & Manager...")
    async with async_session_factory() as session:
        manager = NewsManager(session)
        logger.info("✅ Manager initialized.")
        
        # 3. Test Harvester (Real API Call)
        logger.info("3️⃣ Testing Harvester (Perplexity API)...")
        try:
            # Short query to save tokens
            news_items = await client.search_news(query="AI News", exclude_titles=[])
            logger.info(f"✅ Harvester returned {len(news_items)} items.")
            
            if news_items:
                item = news_items[0]
                logger.info(f"   Sample: {item.title} ({item.source_url})")
                
                # 4. Test Ingestion (Manager)
                logger.info("4️⃣ Testing Ingestion (Save to DB)...")
                count = await manager.add_news_items([item])
                logger.info(f"✅ Added {count} items to DB.")
                
            else:
                logger.warning("⚠️ Harvester returned 0 items. Check API Key or Model.")
                
        except Exception as e:
            logger.error(f"❌ Harvester/Ingestion failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

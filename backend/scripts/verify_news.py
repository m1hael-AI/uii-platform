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
    
    # Init Client
    client = PerplexityClient()
    logger.info(f"🔑 API Key: {client.api_key[:5]}... (Length: {len(client.api_key or '')})")
    logger.info(f"🤖 Model: {client.model}")

    # 1. Check Prompts
    logger.info("1️⃣ Checking Prompts Loading...")
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
                
                # 5. Test Article Generation (Writer)
                logger.info("5️⃣ Testing Article Generation (Writer)...")
                try:
                    article = await client.generate_article(item)
                    if article:
                        logger.info(f"✅ Generated Article: {article.title}")
                        logger.info(f"   Content Length: {len(article.content)} chars")
                    else:
                        logger.warning("⚠️ Writer returned None (check logic/logs).")
                except Exception as w_e:
                    logger.error(f"❌ Writer failed: {w_e}")

                
            else:
                logger.warning("⚠️ Harvester returned 0 items.")
                
        except Exception as e:
            logger.error(f"❌ Harvester failed: {e}")
            
            # --- Fallback Test ---
            logger.info("🔁 Attempting fallback test (Google Gemini)...")
            original_model = client.model
            client.model = "google/gemini-2.0-flash-001"
            try:
                # Manual request bypassing strict JSON for simple check
                messages = [{"role": "user", "content": "Say hello"}]
                # Note: This will likely fail strict JSON validation in _request unless we relax it 
                # or create a special method. But _request expects JSON.
                # Let's try searching news with Gemini
                
                news_items = await client.search_news(query="AI News")
                if news_items:
                     logger.info("✅ Fallback (Gemini) worked! The issue is with PERPLEXITY model availability.")
                else:
                     logger.info("⚠️ Fallback (Gemini) returned 0 items, but no error.")
            except Exception as e2:
                logger.error(f"❌ Fallback failed too: {e2}")
                logger.error("👉 Check your OPENROUTER_API_KEY in .env file!")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

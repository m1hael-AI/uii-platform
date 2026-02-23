"""
backfill_s3_news_images.py

Этот скрипт тестирует новую логику (goose3 -> WebP -> S3).
Запускается отдельно. Обновляет image_url на S3-ссылку.
"""

import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy import select
from database import async_session_factory
from models import NewsItem

from services.news.image_processor import extract_and_upload_best_image


async def backfill_to_s3():
    logger.info("🚀 Starting news image backfill to S3 (Goose3 -> WebP -> S3)...")

    async with async_session_factory() as db:
        result = await db.execute(select(NewsItem).order_by(NewsItem.id))
        news_list = result.scalars().all()

    total = len(news_list)
    logger.info(f"📰 Found {total} news items total.")

    if total == 0:
        logger.info("✅ Nothing to do.")
        return

    found = 0
    skipped = 0

    for i, news in enumerate(news_list, 1):
        urls = news.source_urls or []
        if not urls:
            logger.info(f"[{i}/{total}] ID={news.id} — no source_urls, skip")
            skipped += 1
            continue

        logger.info(f"\n[{i}/{total}] ID={news.id} — Processing {len(urls)} source URL(s) for S3 extraction...")
        s3_url = await extract_and_upload_best_image(urls)

        if s3_url:
            async with async_session_factory() as db:
                item = await db.get(NewsItem, news.id)
                if item:
                    item.image_url = s3_url
                    await db.commit()
            logger.success(f"  ✅ Saved S3 Image: {s3_url}")
            found += 1
        else:
            logger.warning(f"  ❌ Failed to extract any valid image to S3 for ID={news.id}")
            skipped += 1

        await asyncio.sleep(0.5)

    logger.info(
        f"\n🏁 Done. Processed to S3: {found}/{total}, failed/skipped: {skipped}/{total}"
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(backfill_to_s3())

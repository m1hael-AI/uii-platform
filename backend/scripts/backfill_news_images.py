"""
backfill_news_images.py

Проходит по всем новостям без картинки и пытается достать og:image
из source_urls. Сохраняет первую найденную.

Запуск (внутри контейнера или с активированным venv):
    python scripts/backfill_news_images.py

Или через docker:
    docker exec uii-backend python scripts/backfill_news_images.py
"""

import sys
import os
import asyncio
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from loguru import logger
from sqlalchemy import select
from database import async_session_factory
from models import NewsItem

# ---- Настройки ----
REQUEST_TIMEOUT = 6.0      # секунд на один HTTP-запрос
DELAY_BETWEEN = 0.3        # пауза между запросами (чтобы не флудить)
USER_AGENT = "Mozilla/5.0 (compatible; UII-Backfiller/1.0)"

OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\'>\s]+)["\']',
    re.IGNORECASE,
)
# Второй вариант — content перед property
OG_IMAGE_RE2 = re.compile(
    r'<meta[^>]+content=["\'](https?://[^"\'>\s]+)["\'][^>]+property=["\']og:image["\']',
    re.IGNORECASE,
)


async def fetch_og_image(url: str, client: httpx.AsyncClient) -> str | None:
    """Делает GET на url и ищет og:image. Возвращает URL картинки или None."""
    try:
        r = await client.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        if r.status_code != 200:
            return None
        html = r.text
        m = OG_IMAGE_RE.search(html) or OG_IMAGE_RE2.search(html)
        if m:
            return m.group(1).strip()
    except Exception as e:
        logger.warning(f"  ⚠️  GET {url[:80]} failed: {e}")
    return None


async def backfill():
    logger.info("🚀 Starting news image backfill...")

    async with async_session_factory() as db:
        # Только новости без картинки
        result = await db.execute(
            select(NewsItem)
            .where(NewsItem.image_url.is_(None))
            .order_by(NewsItem.id)
        )
        news_list = result.scalars().all()

    total = len(news_list)
    logger.info(f"📰 Found {total} news items without image_url")

    if total == 0:
        logger.info("✅ Nothing to do.")
        return

    found = 0
    skipped = 0

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        for i, news in enumerate(news_list, 1):
            urls = news.source_urls or []
            if not urls:
                logger.info(f"[{i}/{total}] ID={news.id} — no source_urls, skip")
                skipped += 1
                continue

            logger.info(f"[{i}/{total}] ID={news.id} — trying {len(urls)} URL(s)...")
            image_url = None

            for url in urls:
                image_url = await fetch_og_image(url, client)
                if image_url:
                    logger.info(f"  ✅ Found: {image_url[:100]}")
                    break
                await asyncio.sleep(DELAY_BETWEEN)

            if image_url:
                # Сохраняем в отдельной сессии на каждую запись
                async with async_session_factory() as db:
                    item = await db.get(NewsItem, news.id)
                    if item:
                        item.image_url = image_url
                        await db.commit()
                found += 1
            else:
                logger.info(f"  ❌ No og:image found for ID={news.id}")
                skipped += 1

            await asyncio.sleep(DELAY_BETWEEN)

    logger.info(
        f"\n🏁 Done. Updated: {found}/{total}, skipped/not found: {skipped}/{total}"
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(backfill())

"""
backfill_news_images.py

Проходит по всем новостям и пытается достать лучшее изображение из source_urls.
Перебирает og:image + twitter:image, фильтрует мусорные паттерны.

Запуск:
    docker exec ai_university_backend python scripts/backfill_news_images.py
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
REQUEST_TIMEOUT = 6.0
DELAY_BETWEEN = 0.3
USER_AGENT = "Mozilla/5.0 (compatible; UII-Backfiller/1.0)"

# Паттерны для отсева мусорных картинок
_BAD_PATTERNS = re.compile(
    r"(logo|icon|favicon|avatar|pixel|spacer|1x1|badge|banner_small|placeholder|default[-_]img|\.gif)",
    re.IGNORECASE,
)

# og:image — property перед content и наоборот
_OG_RE = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\'>\s]+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\'](https?://[^"\'>\s]+)["\'][^>]+property=["\']og:image["\']', re.IGNORECASE),
]
# twitter:image
_TW_RE = [
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\'](https?://[^"\'>\s]+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\'](https?://[^"\'>\s]+)["\'][^>]+name=["\']twitter:image["\']', re.IGNORECASE),
]


def _extract_best_image(html: str) -> str | None:
    """
    Ищет og:image и twitter:image, возвращает первый прошедший фильтр.
    Порядок: og:image → twitter:image.
    """
    candidates = []
    for patterns in (_OG_RE, _TW_RE):
        for p in patterns:
            m = p.search(html)
            if m:
                candidates.append(m.group(1).strip())
                break  # нашли для этого типа, дальше не ищем

    for url in candidates:
        if not _BAD_PATTERNS.search(url):
            return url

    # Если все найденные картинки мусорные (logo, .gif и т.д.) - возвращаем None, чтобы скрипт перешел к следующему URL
    return None


async def fetch_og_image(url: str, client: httpx.AsyncClient) -> str | None:
    try:
        r = await client.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        if r.status_code != 200:
            return None
        return _extract_best_image(r.text)
    except Exception as e:
        logger.warning(f"  ⚠️  GET {url[:80]} failed: {e}")
    return None


async def backfill():
    logger.info("🚀 Starting news image backfill (overwrite mode, improved filtering)...")

    async with async_session_factory() as db:
        # Все новости (перезаписываем существующие картинки тоже)
        result = await db.execute(select(NewsItem).order_by(NewsItem.id))
        news_list = result.scalars().all()

    total = len(news_list)
    logger.info(f"📰 Found {total} news items total (will overwrite existing images)")

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
                async with async_session_factory() as db:
                    item = await db.get(NewsItem, news.id)
                    if item:
                        item.image_url = image_url
                        await db.commit()
                found += 1
            else:
                logger.info(f"  ❌ No image found for ID={news.id}")
                skipped += 1

            await asyncio.sleep(DELAY_BETWEEN)

    logger.info(
        f"\n🏁 Done. Updated: {found}/{total}, no image found: {skipped}/{total}"
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(backfill())

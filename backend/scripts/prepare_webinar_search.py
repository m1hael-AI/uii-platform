"""
Скрипт подготовки AI-поиска по вебинарам.

Для каждого вебинара в WebinarLibrary генерирует:
  1. short_description  — краткое саммари (2-3 предложения) через gpt-4.1-mini
                          используется ТОЛЬКО в LLM re-ranking (не показывается пользователям)
  2. search_embedding   — вектор (title + description) через text-embedding-3-small
                          используется для cosine search

Запуск:
    cd backend
    python scripts/prepare_webinar_search.py

Флаги:
    --force   — перегенерировать даже если поля уже заполнены
    --dry-run — только показать, что будет обработано (без записи в БД)
"""
import asyncio
import os
import sys
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from loguru import logger
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

from database import async_engine
from models import WebinarLibrary
from services.openai_service import generate_embedding

# Логирование
logger.add("prepare_webinar_search.log", rotation="10 MB", level="INFO")

SUMMARY_MODEL = "gpt-4.1-mini"
SUMMARY_PROMPT = """Ты помощник, который создаёт краткие аннотации для вебинаров.

На вход ты получаешь название и описание вебинара. Твоя задача — написать 2-3 предложения,
кратко передающих суть темы. Не пиши слова "вебинар", "спикер", "запись". Только суть контента.

Название: {title}
Описание: {description}

Напиши только аннотацию, без заголовков и лишних слов."""


async def get_db_session() -> AsyncSession:
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session()


async def generate_short_description(client: AsyncOpenAI, title: str, description: str) -> str:
    """Генерирует краткое описание вебинара через LLM (2-3 предложения)."""
    prompt = SUMMARY_PROMPT.format(
        title=title,
        description=description or "Описание не указано"
    )
    
    response = await client.chat.completions.create(
        model=SUMMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3
    )
    
    return response.choices[0].message.content.strip()


async def prepare_search(force: bool = False, dry_run: bool = False):
    logger.info(f"🚀 Starting webinar search preparation (force={force}, dry_run={dry_run})")
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async with await get_db_session() as db:
        # Загружаем все вебинары
        result = await db.execute(select(WebinarLibrary).order_by(WebinarLibrary.id))
        webinars = result.scalars().all()
        
        logger.info(f"Found {len(webinars)} webinars in library")
        
        processed = 0
        skipped = 0
        errors = 0
        
        for webinar in webinars:
            needs_summary = force or not webinar.short_description
            needs_embedding = force or webinar.search_embedding is None
            
            if not needs_summary and not needs_embedding:
                logger.info(f"  ⏭️  [{webinar.id}] '{webinar.title}' — already prepared, skipping")
                skipped += 1
                continue
            
            logger.info(f"  🔄 [{webinar.id}] Processing: '{webinar.title}'")
            
            if dry_run:
                logger.info(f"     [DRY-RUN] Would generate: summary={needs_summary}, embedding={needs_embedding}")
                continue
            
            try:
                # 1. Краткое описание через LLM
                if needs_summary:
                    short_desc = await generate_short_description(
                        client,
                        title=webinar.title,
                        description=webinar.description or ""
                    )
                    webinar.short_description = short_desc
                    logger.info(f"     ✅ short_description: {short_desc[:80]}...")
                
                # 2. Embedding по title + description
                if needs_embedding:
                    text_to_embed = f"{webinar.title}\n\n{webinar.description or ''}"
                    embedding = await generate_embedding(text_to_embed)
                    webinar.search_embedding = embedding
                    logger.info(f"     ✅ embedding generated ({len(embedding)} dims)")
                
                db.add(webinar)
                await db.commit()
                processed += 1
                logger.info(f"     💾 Saved [{webinar.id}]")
                
            except Exception as e:
                logger.error(f"     ❌ Error processing [{webinar.id}] '{webinar.title}': {e}")
                await db.rollback()
                errors += 1
    
    logger.info(
        f"\n🎉 Done! Processed: {processed}, Skipped: {skipped}, Errors: {errors}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare webinar AI search data")
    parser.add_argument("--force", action="store_true", help="Regenerate even if already filled")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be done")
    args = parser.parse_args()
    
    asyncio.run(prepare_search(force=args.force, dry_run=args.dry_run))

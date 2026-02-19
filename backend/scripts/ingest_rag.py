import asyncio
import os
import sys
from typing import List
from datetime import datetime

# Add parent directory to path to import models and config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from loguru import logger
from dotenv import load_dotenv

# Imports
import re
import nltk
from nltk.tokenize import sent_tokenize

# Ensure NLTK data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Project imports
from database import async_engine
from models import WebinarLibrary, WebinarChunk
from services.openai_service import generate_embedding, generate_embeddings_batch

load_dotenv()

# Setup Logging
logger.add("ingest_rag.log", rotation="10 MB")

# ═══════════════════════════════════════════════════════
# RAG INGESTION CONFIG — все параметры нарезки здесь
# ═══════════════════════════════════════════════════════
RAG_INGEST_CONFIG = {
    "chunk_size_chars": 800,   # Целевой размер чанка в символах (~5-6 VTT-блоков, ~1-2 мин)
    "overlap_blocks":   1,     # Блоков перекрытия (было 2, уменьшили для скорости и снижения дублей)
    "batch_size":       50,    # Размер батча для эмбеддинга (Вернули 50, так как пофиксили размер чанков)
}

async def get_db_session() -> AsyncSession:
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session()

def parse_vtt_blocks(text: str) -> List[str]:
    """
    Парсит VTT-транскрипцию в список атомарных блоков.
    Каждый блок — строка вида "HH:MM:SS --> HH:MM:SS\nТекст речи".
    """
    # Нормализуем переносы строк.
    # Порядок важен: сначала литеральные escape-последовательности (4 символа: \r\n),
    # потом реальные байты CRLF (2 байта). Оба варианта встречаются в зависимости
    # от того, как транскрипт был загружен в БД.
    text = text.replace('\\r\\n', '\n').replace('\\r', '\n').replace('\\n', '\n')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 1. Пробуем стандартный VTT: "00:00:00.000 --> 00:00:00.000"
    ts_pattern_vtt = re.compile(
        r'(\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3})'
    )
    positions = [(m.start(), m.end()) for m in ts_pattern_vtt.finditer(text)]
    
    # 2. Если VTT не найден, пробуем упрощенный формат в скобках [MM:SS...]
    # Сделали регулярку более "жадной" и гибкой к пробелам
    if not positions:
        # Ищем паттерн [цифры:цифры ... ]:
        ts_pattern_brackets = re.compile(
            r'\[(\d{1,2}:\d{2}.*?)\]:'
        )
        positions = [(m.start(), m.end()) for m in ts_pattern_brackets.finditer(text)]

    blocks = []
    for i, (start, end) in enumerate(positions):
        timestamp = text[start:end].strip()
        content_end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        content = text[end:content_end].strip()
        if content:
            blocks.append(f"{timestamp}\n{content}")
    
    return blocks


def chunk_text_vtt(
    text: str,
    chunk_size: int = RAG_INGEST_CONFIG["chunk_size_chars"],
    overlap_blocks: int = RAG_INGEST_CONFIG["overlap_blocks"],
) -> List[str]:
    """
    Режет VTT-транскрипцию на чанки строго по границам timestamp-блоков.
    Гарантирует что чанки не разрываются внутри одного блока.
    Добавляет overlap_blocks блоков из конца предыдущего чанка.
    Fallback на NLTK если VTT-структура не обнаружена.
    """
    blocks = parse_vtt_blocks(text)
    
    if not blocks:
        logger.error(
            f"⚠️ FALLBACK: VTT-блоки не найдены в тексте ({len(text)} символов), "
            f"применена NLTK-нарезка. Проверь формат транскрипта!"
        )
        return chunk_text_nltk(text)
    
    chunks = []
    current_blocks: List[str] = []
    current_size = 0
    
    for block in blocks:
        block_size = len(block)
        
        # SAFETY CHECK: Если блок гигантский (> 4000 символов), рубим его принудительно
        # Это защитит от ошибок OpenAI (8192 токена), если таймкоды вдруг редкие или пропущены
        if block_size > 4000:
            # SAFETY CHECK: Если блок огромный (>4000), рубим его на части, 
            # стараясь сохранить границы предложений (точка, ?, ! + пробел)
            
            # 1. Разбиваем на предложения
            sentences = re.split(r'(?<=[.!?])\s+', block)
            
            sub_chunk = []
            sub_chunk_size = 0
            
            for sentence in sentences:
                sent_len = len(sentence)
                
                # Если само предложение гигантское (> chunk_size * 2), рубим жестко
                # (защита от "висящих" кусков кода или логов без точек)
                if sent_len > chunk_size * 2:
                    # Сначала сбрасываем накопленное
                    if sub_chunk:
                        chunks.append(' '.join(sub_chunk))
                        sub_chunk = []
                        sub_chunk_size = 0
                    
                    # Рубим длинное предложение по chunk_size
                    for part in range(0, sent_len, chunk_size):
                        chunks.append(sentence[part : part + chunk_size])
                    continue

                # Если добавление предложения превысит chunk_size
                if sub_chunk_size + sent_len > chunk_size and sub_chunk:
                    chunks.append(' '.join(sub_chunk))
                    sub_chunk = []
                    sub_chunk_size = 0
                
                sub_chunk.append(sentence)
                sub_chunk_size += sent_len
            
            # Добавляем остаток
            if sub_chunk:
                chunks.append(' '.join(sub_chunk))
            
            continue # Блок обработан и нарезан по предложениям/кускам

        if current_size + block_size > chunk_size and current_blocks:
            chunks.append('\n\n'.join(current_blocks))
            # Overlap: первые блоки следующего чанка = последние N блоков текущего
            current_blocks = current_blocks[-overlap_blocks:] if overlap_blocks > 0 else []
            current_size = sum(len(b) for b in current_blocks)
        
        current_blocks.append(block)
        current_size += block_size
    
    if current_blocks:
        chunks.append('\n\n'.join(current_blocks))
    
    return chunks


def chunk_text_nltk(text: str, chunk_size: int = 1000) -> List[str]:
    """Fallback: NLTK-нарезка по предложениям (используется если VTT не распознан)."""
    sentences = sent_tokenize(text, language="russian")
    chunks, current_chunk = [], ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

async def ingest_webinars():
    logger.info(f"🚀 Starting RAG Ingestion (Batch Size: {RAG_INGEST_CONFIG['batch_size']}, Overlap: {RAG_INGEST_CONFIG['overlap_blocks']})...")
    
    async with await get_db_session() as db:
        # 1. Fetch all webinars with transcripts
        logger.info("Fetching webinars...")
        result = await db.execute(select(WebinarLibrary).where(WebinarLibrary.transcript_context != None))
        webinars = result.scalars().all()
        
        logger.info(f"Found {len(webinars)} webinars with transcripts.")
        
        total_chunks_created = 0
        
        for webinar in webinars:
            if not webinar.transcript_context.strip():
                continue
            
            # Skip already successfully processed webinars (1-39)
            if webinar.id not in [41, 50, 55]:
                # logger.info(f"Skipping webinar {webinar.id} (already ingested or not targeted)")
                continue

            logger.info(f"Processing webinar: {webinar.title} (ID: {webinar.id})")
            
            # 2. Cleanup old chunks for this webinar (to avoid duplicates on rerun)
            await db.execute(delete(WebinarChunk).where(WebinarChunk.webinar_id == webinar.id))
            
            # 3. Chunking по VTT-блокам (параметры — RAG_INGEST_CONFIG выше)
            text = webinar.transcript_context
            chunks_text = chunk_text_vtt(text)
            logger.info(f"  -> Split into {len(chunks_text)} VTT-chunks.")
            
            # 4. Embedding & Saving (Batch Mode)
            webinar_chunks = []
            
            # Разбиваем на батчи по RAG_INGEST_CONFIG["batch_size"]
            batch_size = RAG_INGEST_CONFIG["batch_size"]
            total_chunks = len(chunks_text)
            
            for i in range(0, total_chunks, batch_size):
                batch_texts = chunks_text[i : i + batch_size]
                current_batch_indices = range(i, i + len(batch_texts))
                
                try:
                    # Генерируем векторы пачкой (1 запрос вместо 50)
                    vectors = await generate_embeddings_batch(batch_texts)
                    
                    for text_content, vector, idx in zip(batch_texts, vectors, current_batch_indices):
                        db_chunk = WebinarChunk(
                            webinar_id=webinar.id,
                            content=text_content,
                            embedding=vector,
                            chunk_metadata={
                                "index": idx,
                                "source": "transcript",
                                "title": webinar.title
                            }
                        )
                        db.add(db_chunk)
                    
                    total_chunks_created += len(batch_texts)
                    logger.info(f"    -> Processed batch {i}-{i+len(batch_texts)}/{total_chunks}")
                    
                except Exception as e:
                    logger.error(f"  ❌ Failed to embed batch {i}: {e}")

            # Commit per webinar to save progress
            await db.commit()
            logger.info(f"  ✅ Saved {total_chunks} chunks for '{webinar.title}'")
            
    logger.info(f"🎉 Ingestion Complete! Total chunks: {total_chunks_created}")

if __name__ == "__main__":
    # Ensure NLTK data is available (if not in docker)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
        
    asyncio.run(ingest_webinars())

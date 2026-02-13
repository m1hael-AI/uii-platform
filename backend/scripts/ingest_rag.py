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

# NLTK imports
import nltk
from nltk.tokenize import sent_tokenize

# Project imports
from database import async_engine
from models import WebinarLibrary, WebinarChunk
from services.openai_service import generate_embedding

load_dotenv()

# Setup Logging
logger.add("ingest_rag.log", rotation="10 MB")

async def get_db_session() -> AsyncSession:
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session()

def chunk_text_nltk(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Режет текст на чанки по предложениям с помощью NLTK.
    Старается собрать предложения в чанк размером ~chunk_size символов.
    """
    sentences = sent_tokenize(text, language="russian")
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # Если добавление предложения не превышает лимит (или чанк пустой)
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence + " "
        else:
            # Чанк заполнен, сохраняем
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Начинаем новый чанк
            # TODO: Реализовать overlap (сложнее с предложениями, пока просто стык)
            # Для простоты MVP overlap делаем "на глаз" - можно брать последнее предложение
            # Но сейчас сделаем без оверлапа для чистоты эксперимента
            current_chunk = sentence + " "
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

async def ingest_webinars():
    logger.info("🚀 Starting RAG Ingestion...")
    
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
                
            logger.info(f"Processing webinar: {webinar.title} (ID: {webinar.id})")
            
            # 2. Cleanup old chunks for this webinar (to avoid duplicates on rerun)
            await db.execute(delete(WebinarChunk).where(WebinarChunk.webinar_id == webinar.id))
            
            # 3. Chunking
            text = webinar.transcript_context
            # NLTK split
            chunks_text = chunk_text_nltk(text)
            logger.info(f"  -> Split into {len(chunks_text)} chunks.")
            
            # 4. Embedding & Saving
            webinar_chunks = []
            for i, chunk_content in enumerate(chunks_text):
                # Generate Embedding
                # Note: This calls OpenAI API, cost money!
                try:
                    vector = await generate_embedding(chunk_content)
                    
                    db_chunk = WebinarChunk(
                        webinar_id=webinar.id,
                        content=chunk_content,
                        embedding=vector,
                        chunk_metadata={
                            "index": i,
                            "source": "transcript",
                            "title": webinar.title
                        }
                    )
                    db.add(db_chunk)
                    total_chunks_created += 1
                except Exception as e:
                    logger.error(f"  ❌ Failed to embed chunk {i}: {e}")
            
            # Commit per webinar to save progress
            await db.commit()
            logger.info(f"  ✅ Saved {len(chunks_text)} chunks for '{webinar.title}'")
            
    logger.info(f"🎉 Ingestion Complete! Total chunks: {total_chunks_created}")

if __name__ == "__main__":
    # Ensure NLTK data is available (if not in docker)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
        
    asyncio.run(ingest_webinars())

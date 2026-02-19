"""
Сервис для RAG (Retrieval-Augmented Generation).
Отвечает за ПОИСК релевантных кусков знаний в базе данных.
Логика нарезки (Ingestion) вынесена в отдельный скрипт.
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from loguru import logger
from models import WebinarChunk
from services.openai_service import generate_embedding

async def search_relevant_chunks(
    db: AsyncSession,
    query: str,
    limit: int = 8,            # Было 5 — слишком мало для длинных вебинаров
    similarity_threshold: float = 0.75,  # Было 0.65 — слишком строго, нужные чанки отсекались
    webinar_id: int = None
) -> List[WebinarChunk]:
    """
    Ищет в базе вебинаров фрагменты, похожие на запрос пользователя.
    Использует Cosine Distance (<=>) оператор pgvector.
    """
    try:
        # 1. Генерируем вектор запроса
        query_vector = await generate_embedding(query)
        
        # 2. SQL запрос с сортировкой по дистанции
        stmt = select(WebinarChunk)
        
        # Filter by webinar if specified
        if webinar_id:
            stmt = stmt.where(WebinarChunk.webinar_id == webinar_id)
            
        # Filter by Similarity Threshold
        # Cosine Distance: 0.0 (Same) -> 1.0 (Different). 
        # We want meaningful matches, so distance must be SMALLER than threshold.
        # Note: 0.5 is usually a loose match, 0.3 is strict.
        distance_col = WebinarChunk.embedding.cosine_distance(query_vector)
        stmt = stmt.where(distance_col < similarity_threshold)
            
        stmt = stmt.order_by(distance_col).limit(limit)
        
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        return chunks
        
    except Exception as e:
        logger.error(f"❌ Error in RAG search: {e}")
        return []

async def format_rag_context(chunks: List[WebinarChunk]) -> str:
    """
    Форматирует найденные чанки в строку для System Prompt.
    """
    if not chunks:
        return ""
        
    context_str = "=== ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ (ВЕБИНАРЫ) ===\n"
    for i, chunk in enumerate(chunks, 1):
        context_str += f"[{i}] {chunk.content}\n"
        
    return context_str

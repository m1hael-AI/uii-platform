from typing import List, Optional
import json
import os
import time as time_module
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from openai import AsyncOpenAI

from database import get_async_session
from models import User, NewsItem, NewsStatus
from dependencies import get_current_user, check_news_rate_limit
from services.news.manager import NewsManager
from services.audit_service import fire_and_forget_audit



router = APIRouter(prefix="/news", tags=["News"])

@router.get("/", response_model=List[dict])  # Simplification: returning dicts to avoid Pydantic overhead for now
async def get_news_list(
    status: Optional[NewsStatus] = None,
    type: str = Query("all", regex="^(all|foryou)$"),
    q: Optional[str] = Query(None, description="Поисковый запрос для векторного поиска"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user)
):
    """
    Получить список новостей с пагинацией.
    type: "all" (хронология) или "foryou" (персонализация)
    q: поисковый запрос (если есть - включается векторный поиск)
    """
    manager = NewsManager(db)

    if q:
        # Vector Search Mode (High Priority)
        # Ignores type=foryou mostly, as query is explicit intent
        news = await manager.search_local_news(query=q, limit=limit)
        
    elif type == "foryou":
        # Personalized feed (no status filter support yet, usually returns all valid)
        news = await manager.get_personalized_news(user_id=user.id, limit=limit)
        # Offset logic is hard with personalization (re-ranking), 
        # for now simplistic slice or just ignore offset in manager (manager limit handles top N)
        # But `get_personalized_news` returns limit items. 
        # Pagination in personalization is complex. Let's assume infinite scroll just asks for next page?
        # Actually simplest is: Manager returns top N. If offset > 0, we might miss things or see dupes if re-ranked.
        # MVP: "For You" ignores offset or we implement detailed pagination later. 
        # Current manager impl ignores offset.
        
    else:
        # Standard feed
        stmt = select(NewsItem).order_by(desc(NewsItem.published_at)).limit(limit).offset(offset)
        
        if status:
            stmt = stmt.where(NewsItem.status == status)
            
        result = await db.execute(stmt)
        news = result.scalars().all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "summary": n.summary,
            "image_url": n.image_url,
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "status": n.status,
            "tags": n.tags,
            "source_urls": n.source_urls
        }
        for n in news
    ]

# === AI Search Config ===
_NEWS_SEARCH_RERANK_MODEL = "gpt-4.1-mini"
_NEWS_SEARCH_VECTOR_LIMIT = 20

_NEWS_RERANK_PROMPT = """Ты — помощник, который оценивает релевантность новостей поисковому запросу.

Запрос пользователя: "{query}"

Список новостей (JSON):
{news_json}

Верни ТОЛЬКО JSON со списком ID новостей, которые реально отвечают на запрос.
Если новость лишь косвенно связана или вообще не связана — не включай её.
Формат ответа (строго JSON, без лишнего текста):
{{"relevant_ids": [1, 3, 7]}}"""


@router.get("/ai-search", response_model=List[dict])
async def ai_search_news(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user)
):
    """
    AI-поиск по новостям в базе данных.
    1. Векторный поиск по embedding (title+summary)
    2. LLM Re-ranking через gpt-4.1-mini
    3. Fallback на текстовый поиск (логируется)
    """
    _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    manager = NewsManager(db)

    # === Шаг 1: Векторный поиск ===
    candidates = await manager.search_local_news(query=q, limit=_NEWS_SEARCH_VECTOR_LIMIT)

    # === Fallback: Текстовый поиск ===
    if not candidates:
        logger.warning(
            f"⚠️ NewsAISearch: falling back to text search for query: '{q}' "
            f"(reason: no embeddings or vector search error)"
        )
        stmt = select(NewsItem).where(
            NewsItem.title.ilike(f"%{q}%")
        ).order_by(desc(NewsItem.published_at)).limit(_NEWS_SEARCH_VECTOR_LIMIT)
        result = await db.execute(stmt)
        candidates = result.scalars().all()

        return [
            {
                "id": n.id,
                "title": n.title,
                "summary": n.summary,
                "image_url": n.image_url,
                "published_at": n.published_at.isoformat() if n.published_at else None,
                "status": n.status,
                "tags": n.tags,
                "source_urls": n.source_urls
            }
            for n in candidates
        ]

    if not candidates:
        return []

    # === Шаг 2: LLM Re-ranking ===
    news_for_llm = [
        {
            "id": n.id,
            "title": n.title,
            "summary": n.summary[:200] if n.summary else "Нет описания"
        }
        for n in candidates
    ]

    try:
        prompt = _NEWS_RERANK_PROMPT.format(
            query=q,
            news_json=json.dumps(news_for_llm, ensure_ascii=False, indent=2)
        )
        messages = [{"role": "user", "content": prompt}]

        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        t0 = time_module.time()
        response = await _client.chat.completions.create(
            model=_NEWS_SEARCH_RERANK_MODEL,
            messages=messages,
            max_tokens=200,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        duration_ms = int((time_module.time() - t0) * 1000)

        llm_output = json.loads(response.choices[0].message.content)
        relevant_ids = set(llm_output.get("relevant_ids", []))

        # Аудит-лог LLM
        fire_and_forget_audit(
            user_id=user.id,
            agent_slug="news_ai_search",
            model=_NEWS_SEARCH_RERANK_MODEL,
            messages=messages,
            response_content=response.choices[0].message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            duration_ms=duration_ms,
            cost_usd_api=None  # Считаем по таблице PRICES
        )

        logger.info(
            f"🔍 NewsAISearch: query='{q}', candidates={len(candidates)}, "
            f"relevant_after_rerank={len(relevant_ids)}, tokens={response.usage.total_tokens}"
        )

        id_to_news = {n.id: n for n in candidates}
        ranked_news = [id_to_news[nid] for nid in relevant_ids if nid in id_to_news]

    except Exception as e:
        logger.error(f"❌ NewsAISearch: LLM re-ranking failed, returning all candidates: {e}")
        ranked_news = candidates

    return [
        {
            "id": n.id,
            "title": n.title,
            "summary": n.summary,
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "status": n.status,
            "tags": n.tags,
            "source_urls": n.source_urls
        }
        for n in ranked_news
    ]


@router.get("/{news_id}", response_model=dict)
async def get_news_item(
    news_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Получить новость по ID.
    """
    news = await db.get(NewsItem, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News item not found")
        
    return {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "summary": news.summary,
        "published_at": news.published_at.isoformat() if news.published_at else None,
        "status": news.status,
        "tags": news.tags,
        "source_urls": news.source_urls,
        "updated_at": news.updated_at.isoformat() if news.updated_at else None
    }


@router.post("/search", response_model=dict)

async def search_fresh_news(
    request: dict = Body(...),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user),
    _ = Depends(check_news_rate_limit)
):
    """
    Поиск свежих новостей через Perplexity API.
    Найденные новости сохраняются в базу со статусом PENDING.
    """
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    manager = NewsManager(db)
    try:
        # 1. Hybrid Search: Get Context from Vector DB
        context = await manager.find_context_for_query(query)
        
        # 2. Search for news using Perplexity with Context
        news_items = await manager.perplexity.search_news(query=query, context=context)
        
        if not news_items:
            return {"results": [], "message": "No news found for this query"}
        
        # Add news items to database
        added_count = await manager.add_news_items(news_items)
        
        # Fetch the newly added items to return to frontend
        stmt = select(NewsItem).order_by(desc(NewsItem.created_at)).limit(len(news_items))
        result = await db.execute(stmt)
        new_news = result.scalars().all()
        
        return {
            "results": [
                {
                    "id": n.id,
                    "title": n.title,
                    "summary": n.summary,
                    "published_at": n.published_at.isoformat() if n.published_at else None,
                    "status": n.status,
                    "tags": n.tags,
                    "source_urls": n.source_urls,
                    "image_url": n.image_url
                }
                for n in new_news
            ],
            "message": f"Found {added_count} new articles"
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/{news_id}/generate", response_model=dict)
async def generate_article_manual(
    news_id: int,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user)  # Any authenticated user
):
    """
    Принудительно запустить генерацию для новости.
    Доступно для любого авторизованного пользователя.
    Генерация происходит только для новостей со статусом PENDING.
    """
    # Check if news exists and get its status
    stmt = select(NewsItem).where(NewsItem.id == news_id)
    result = await db.execute(stmt)
    news_item = result.scalar_one_or_none()
    
    if not news_item:
        raise HTTPException(status_code=404, detail="News item not found")
    
    # If already completed, return existing article
    if news_item.status == NewsStatus.COMPLETED:
        return {
            "status": "already_completed",
            "title": news_item.title,
            "content": news_item.content,
            "article": {
                "id": news_item.id,
                "title": news_item.title,
                "summary": news_item.summary,
                "content": news_item.content,
                "status": news_item.status
            }
        }
    
    # If failed, allow retry
    if news_item.status == NewsStatus.FAILED:
        news_item.status = NewsStatus.PENDING
        await db.commit()
    
    # Trigger generation
    manager = NewsManager(db)
    try:
        article = await manager.trigger_generation(news_id)
        if not article:
             raise HTTPException(status_code=400, detail="Generation failed or returned empty")
             
        return {
            "status": "success",
            "title": article.title,
            "article": {
                "id": article.id,
                "title": article.title,
                "summary": article.summary,
                "content": article.content,
                "status": article.status
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

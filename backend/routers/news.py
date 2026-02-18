from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database import get_async_session
from models import User, NewsItem, NewsStatus
from dependencies import get_current_user
from services.news.manager import NewsManager



router = APIRouter(prefix="/news", tags=["News"])

@router.get("/", response_model=List[dict])  # Simplification: returning dicts to avoid Pydantic overhead for now
async def get_news_list(
    status: Optional[NewsStatus] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Получить список новостей с пагинацией.
    """
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
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "status": n.status,
            "tags": n.tags,
            "source_urls": n.source_urls
        }
        for n in news
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
        "content": news.content, # Markdown article
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
    user: User = Depends(get_current_user)
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
                    "source_urls": n.source_urls
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

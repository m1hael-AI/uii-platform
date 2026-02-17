from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

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

@router.post("/{news_id}/generate", response_model=dict)
async def generate_article_manual(
    news_id: int,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user)
):
    """
    Принудительно запустить генерацию для новости.
    """
    # Check if user is admin
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    manager = NewsManager(db)
    try:
        article = await manager.trigger_generation(news_id)
        if not article:
             raise HTTPException(status_code=400, detail="Generation failed or returned empty")
             
        return {"status": "success", "title": article.title}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

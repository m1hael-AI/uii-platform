from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_factory
from dependencies import get_db, get_current_user, check_news_rate_limit
from models import User, NewsItem, NewsStatus
from services.news.manager import NewsManager
from services.news.perplexity import NewsItemSchema

router = APIRouter(prefix="/news", tags=["AI News"])

@router.get("/", response_model=List[NewsItem])
async def get_news_feed(
    limit: int = 20, 
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
    # Open for public or user? Let's say public for now, or authenticated.
    # user: User = Depends(get_current_user) 
):
    """
    Получить ленту новостей.
    """
    manager = NewsManager(db)
    return await manager.get_news_feed(limit, offset)

@router.get("/{news_id}", response_model=NewsItem)
async def get_news_item(
    news_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Получить одну новость.
    """
    manager = NewsManager(db)
    item = await db.get(NewsItem, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    return item

@router.post("/{news_id}/generate", response_model=NewsItem)
async def generate_article_for_news(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    _ = Depends(check_news_rate_limit) # Rate limit check
):
    """
    Запустить генерацию статьи для новости.
    Требует авторизации и лимитируется.
    """
    manager = NewsManager(db)
    
    # Check exists
    item = await db.get(NewsItem, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
        
    # Trigger logic
    # Note: trigger_generation saves to DB internally.
    # To return updated item, we need to refresh or fetch again.
    
    # Since trigger_generation might take time (Perplexity API), 
    # ideally this should be async background task.
    # But for MVP, let's await it (User waits ~10-20s).
    
    try:
        updated_article = await manager.trigger_generation(news_id)
        if not updated_article:
             # If status was already completed or failed without exception
             pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    await db.refresh(item)
    return item

@router.post("/search", response_model=List[NewsItem])
async def search_and_add_news(
    query: str = Query(..., min_length=3),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    _ = Depends(check_news_rate_limit) # Search also costs money
):
    """
    Поиск новостей по запросу (через Perplexity) и добавление их в БД.
    Возвращает новые добавленные новости (или существующие, если дубликаты).
    """
    manager = NewsManager(db)
    
    # 1. Search directly via Manager's client (or Manager should wrap this?)
    # Manager doesn't have public search method yet, it assumes 'add_news_items' gets items.
    # Let's use client directly then add.
    
    try:
        # We need client instance. Manager creates it in __init__
        # But maybe better to expose 'search' in Manager?
        # Let's direct use client for now to keep Manager simple on ingestion.
        
        # But wait, Manager.perplexity is initialized.
        client = manager.perplexity
        
        # Search
        fetched_items = await client.search_news(query=query)
        
        if not fetched_items:
            return []
            
        # Add to DB
        count = await manager.add_news_items(fetched_items)
        
        # Return what we just found/added? 
        # get_news_feed returns everything. 
        # Probably we want to return the items that match the query from DB?
        # For now let's just return the feed (top 5) or the fetched items as preview.
        # Returning NewsItemSchema list (not DB objects) is easier as we don't know IDs of skipped dupes easily.
        
        # Actually, let's return the feed to show they appear.
        return await manager.get_news_feed(limit=len(fetched_items) or 5)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

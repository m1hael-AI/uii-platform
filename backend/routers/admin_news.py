"""
Admin router for AI News management.
Provides endpoints for managing prompts, schedule, and settings.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import get_async_session
from models import User, NewsSettings, NewsItem, NewsStatus, UserRole
from dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/news", tags=["admin-news"])


def verify_admin(user: User):
    """Verify user has admin privileges."""
    from fastapi import HTTPException, status
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin privileges required"
        )


@router.get("/config", response_model=dict)
async def get_news_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить текущие настройки AI News.
    Только для админов.
    """
    verify_admin(current_user)
    
    # Get settings (singleton)
    stmt = select(NewsSettings).limit(1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Create default settings if not exist
        settings = NewsSettings(
            id=1,
            harvester_prompt="You are a news aggregator AI. Find the most important and recent AI/ML news.",
            writer_prompt="You are a professional tech writer. Create a comprehensive article about the given news.",
            harvester_enabled=True,
            harvester_cron="0 2 * * *",
            generator_enabled=True,
            generator_cron="*/15 * * * *",
            dedup_threshold=0.84,
            generator_batch_size=5,
            generator_delay=2
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    # Get stats
    total_news_stmt = select(NewsItem)
    total_result = await db.execute(total_news_stmt)
    total_news = len(total_result.scalars().all())
    
    # Status counts
    pending_stmt = select(NewsItem).where(NewsItem.status == NewsStatus.PENDING)
    pending_result = await db.execute(pending_stmt)
    pending_count = len(pending_result.scalars().all())
    
    completed_stmt = select(NewsItem).where(NewsItem.status == NewsStatus.COMPLETED)
    completed_result = await db.execute(completed_stmt)
    completed_count = len(completed_result.scalars().all())
    
    failed_stmt = select(NewsItem).where(NewsItem.status == NewsStatus.FAILED)
    failed_result = await db.execute(failed_stmt)
    failed_count = len(failed_result.scalars().all())
    
    return {
        "prompts": {
            "harvester": settings.harvester_prompt,
            "writer": settings.writer_prompt
        },
        "schedule": {
            "harvester_cron": settings.harvester_cron,
            "harvester_enabled": settings.harvester_enabled,
            "generator_cron": settings.generator_cron,
            "generator_enabled": settings.generator_enabled
        },
        "settings": {
            "dedup_threshold": settings.dedup_threshold,
            "generator_batch_size": settings.generator_batch_size,
            "generator_delay": settings.generator_delay
        },
        "stats": {
            "total_news": total_news,
            "status_counts": {
                "PENDING": pending_count,
                "COMPLETED": completed_count,
                "FAILED": failed_count
            }
        },
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
    }


@router.put("/config", response_model=dict)
async def update_news_config(
    config: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновить настройки AI News.
    Только для админов.
    """
    verify_admin(current_user)
    
    # Get existing settings
    stmt = select(NewsSettings).limit(1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found. Please use GET first to initialize.")
    
    # Update prompts
    if "prompts" in config:
        if "harvester" in config["prompts"]:
            settings.harvester_prompt = config["prompts"]["harvester"]
        if "writer" in config["prompts"]:
            settings.writer_prompt = config["prompts"]["writer"]
    
    # Update schedule
    if "schedule" in config:
        if "harvester_cron" in config["schedule"]:
            settings.harvester_cron = config["schedule"]["harvester_cron"]
        if "harvester_enabled" in config["schedule"]:
            settings.harvester_enabled = config["schedule"]["harvester_enabled"]
        if "generator_cron" in config["schedule"]:
            settings.generator_cron = config["schedule"]["generator_cron"]
        if "generator_enabled" in config["schedule"]:
            settings.generator_enabled = config["schedule"]["generator_enabled"]
    
    # Update settings
    if "settings" in config:
        if "dedup_threshold" in config["settings"]:
            settings.dedup_threshold = config["settings"]["dedup_threshold"]
        if "generator_batch_size" in config["settings"]:
            settings.generator_batch_size = config["settings"]["generator_batch_size"]
        if "generator_delay" in config["settings"]:
            settings.generator_delay = config["settings"]["generator_delay"]
    
    # Update timestamp
    settings.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(settings)
    
    logger.info(f"News settings updated by admin {current_user.email or current_user.tg_username}")
    
    return {
        "status": "success",
        "message": "Settings updated successfully",
        "updated_at": settings.updated_at.isoformat()
    }

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import ProactivitySettings, ChatSettings
from loguru import logger

async def get_proactivity_settings(db: AsyncSession) -> ProactivitySettings:
    """Получить настройки проактивности (singleton/cache)"""
    # Можно добавить кэширование, если нагрузка будет большой
    result = await db.execute(select(ProactivitySettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        logger.info("⚡ Creating default ProactivitySettings")
        settings = ProactivitySettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


async def get_chat_settings(db: AsyncSession) -> ChatSettings:
    """Получить настройки чата (singleton/cache)"""
    result = await db.execute(select(ChatSettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        logger.info("⚡ Creating default ChatSettings")
        settings = ChatSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings

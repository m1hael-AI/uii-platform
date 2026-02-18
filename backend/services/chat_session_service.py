from datetime import datetime
from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from models import ChatSession, WebinarSchedule, WebinarLibrary
from utils.logger import logger

async def get_or_create_chat_session(
    db: AsyncSession,
    user_id: int,
    agent_slug: str,
    webinar_id: Optional[int] = None,
    news_id: Optional[int] = None,
    is_active: bool = True
) -> ChatSession:
    """
    Атомарное получение или создание сессии чата.
    Гарантирует отсутствие дубликатов при параллельных запросах.
    """
    
    # 1. Определяем контекст (Webinar vs General vs News)
    schedule_id = None
    library_id = None
    
    if webinar_id:
        # Пытаемся понять, это предстоящий вебинар или запись
        res = await db.execute(select(WebinarLibrary).where(WebinarLibrary.id == webinar_id))
        lib = res.scalar_one_or_none()
        if lib:
            library_id = lib.id
        else:
            res_sch = await db.execute(select(WebinarSchedule).where(WebinarSchedule.id == webinar_id))
            sch = res_sch.scalar_one_or_none()
            if sch:
                schedule_id = sch.id

    # 2. Формируем запрос для поиска
    q = select(ChatSession).where(
        ChatSession.user_id == user_id,
        ChatSession.agent_slug == agent_slug,
        ChatSession.schedule_id == schedule_id,
        ChatSession.library_id == library_id,
        ChatSession.news_id == news_id
    )
    
    # 3. Попытка получить существующую сессию
    result = await db.execute(q)
    session = result.scalar_one_or_none()
    
    if session:
        return session
        
    # 4. Если нет - пытаемся создать
    try:
        session = ChatSession(
            user_id=user_id,
            agent_slug=agent_slug,
            schedule_id=schedule_id,
            library_id=library_id,
            news_id=news_id,
            is_active=is_active,
            last_message_at=datetime.utcnow()
        )
        db.add(session)
        # Используем flush, чтобы проверить Unique Constraint в БД до коммита
        await db.flush()
        await db.refresh(session)
        logger.info(f"🆕 Created new ChatSession {session.id} for user {user_id}, agent {agent_slug}")
        return session
        
    except IntegrityError:
        # Race condition: кто-то другой успел создать сессию между нашим SELECT и INSERT
        await db.rollback()
        logger.warning(f"🔄 Race condition detected for user {user_id}, agent {agent_slug}. Retrying fetch.")
        result = await db.execute(q)
        session = result.scalar_one_or_none()
        if session:
            return session
        raise  # Если даже после этого нет, значит какая-то другая ошибка БД

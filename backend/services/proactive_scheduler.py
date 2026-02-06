"""
Планировщик проактивных сообщений AI University.

Компоненты:
1. Проверка тихих часов (по timezone пользователя)
2. Проверка лимитов сообщений (3 для агентов, 3 для AI Помощника)
3. Выбор задач из PendingAction (FIFO)
4. Передача в Executor для отправки
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import pytz
from loguru import logger

from models import PendingAction, User, ProactivitySettings, Message, ChatSession


async def get_user_local_time(user: User) -> datetime:
    """Получить текущее время в timezone пользователя"""
    user_tz = pytz.timezone(user.timezone) if user.timezone else pytz.UTC
    return datetime.now(user_tz)


def is_quiet_hours(user_time: datetime, settings: ProactivitySettings) -> bool:
    """
    Проверить, попадает ли время в тихие часы.
    
    Пример: quiet_hours_start = "22:00", quiet_hours_end = "10:00"
    Тихие часы: с 22:00 до 10:00 следующего дня
    """
    current_hour = user_time.hour
    current_minute = user_time.minute
    current_time_minutes = current_hour * 60 + current_minute
    
    # Парсим время начала и конца
    start_parts = settings.quiet_hours_start.split(":")
    start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
    
    end_parts = settings.quiet_hours_end.split(":")
    end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
    
    # Если конец раньше начала, значит тихие часы переходят через полночь
    if end_minutes < start_minutes:
        # Например: 22:00 - 10:00
        return current_time_minutes >= start_minutes or current_time_minutes < end_minutes
    else:
        # Например: 01:00 - 08:00
        return start_minutes <= current_time_minutes < end_minutes


async def count_messages_today(
    db: AsyncSession,
    user_id: int,
    agent_slug: Optional[str] = None
) -> int:
    """
    Подсчитать количество проактивных сообщений, отправленных сегодня.
    
    Args:
        user_id: ID пользователя
        agent_slug: Если указан, считаем только для этого агента.
                   Если None, считаем для всех агентов (кроме main_assistant)
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = select(func.count(PendingAction.id)).where(
        PendingAction.user_id == user_id,
        PendingAction.status == "sent",
        PendingAction.sent_at >= today_start
    )
    
    if agent_slug:
        # Считаем для конкретного агента
        query = query.where(PendingAction.agent_slug == agent_slug)
    else:
        # Считаем для всех агентов, кроме main_assistant
        query = query.where(PendingAction.agent_slug != "main_assistant")
    
    result = await db.execute(query)
    return result.scalar() or 0


async def can_send_proactive_message(
    db: AsyncSession,
    user_id: int,
    agent_slug: str,
    settings: ProactivitySettings
) -> bool:
    """
    Проверить, можно ли отправить проактивное сообщение.
    
    Проверяет лимиты:
    - Для main_assistant: max_messages_per_day_assistant
    - Для других агентов: max_messages_per_day_agents (общий лимит на всех)
    """
    if agent_slug == "main_assistant":
        # Проверяем лимит для AI Помощника
        count = await count_messages_today(db, user_id, agent_slug="main_assistant")
        return count < settings.max_messages_per_day_assistant
    else:
        # Проверяем общий лимит для всех агентов
        count = await count_messages_today(db, user_id, agent_slug=None)
        return count < settings.max_messages_per_day_agents


async def get_pending_actions_fifo(
    db: AsyncSession,
    settings: ProactivitySettings
) -> List[PendingAction]:
    """
    Получить pending задачи в порядке FIFO (First In, First Out).
    Самые старые задачи обрабатываются первыми.
    """
    if not settings.enabled:
        return []
    
    query = select(PendingAction).where(
        PendingAction.status == "pending"
    ).order_by(
        PendingAction.created_at.asc()  # FIFO: самые старые первыми
    )
    
    result = await db.execute(query)
    return result.scalars().all()


async def process_pending_actions(db: AsyncSession) -> None:
    """
    Основная функция планировщика.
    Запускается каждый час (настраивается в scheduler.py).
    
    Логика:
    1. Получить все pending задачи (FIFO)
    2. Для каждой задачи:
       - Получить пользователя
       - Проверить тихие часы
       - Проверить лимиты
       - Если всё ОК → передать в Executor
    """
    from services.proactive_executor import execute_proactive_message
    from models import ProactivitySettings
    
    # Получаем настройки
    settings_result = await db.execute(select(ProactivitySettings))
    settings = settings_result.scalar_one_or_none()
    
    if not settings or not settings.enabled:
        logger.info("⏸️ Проактивность отключена")
        return
    
    # Получаем pending задачи
    pending_actions = await get_pending_actions_fifo(db, settings)
    
    if not pending_actions:
        logger.info("📭 Нет pending задач")
        return
    
    logger.info(f"📬 Найдено {len(pending_actions)} pending задач")
    
    processed = 0
    skipped = 0
    
    for action in pending_actions:
        try:
            # Получаем пользователя
            user_result = await db.execute(
                select(User).where(User.id == action.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"⚠️ Пользователь {action.user_id} не найден, пропускаем")
                action.status = "failed"
                await db.commit()
                skipped += 1
                continue
            
            # Проверяем тихие часы
            user_time = await get_user_local_time(user)
            if is_quiet_hours(user_time, settings):
                logger.debug(f"🌙 Тихие часы для пользователя {user.id} ({user_time.strftime('%H:%M')}), пропускаем")
                skipped += 1
                continue
            
            # Проверяем лимиты
            if not await can_send_proactive_message(db, user.id, action.agent_slug, settings):
                logger.debug(f"🚫 Лимит сообщений исчерпан для пользователя {user.id}, agent={action.agent_slug}")
                skipped += 1
                continue
            
            # Всё ОК, отправляем в Executor
            logger.info(f"✅ Отправка проактивного сообщения: user={user.id}, agent={action.agent_slug}")
            await execute_proactive_message(db, action, settings)
            processed += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки задачи {action.id}: {e}")
            action.status = "failed"
            await db.commit()
            skipped += 1
            continue
    
    logger.info(f"📊 Обработано: {processed}, Пропущено: {skipped}")

"""
Суммаризатор для проактивности AI University.

Компоненты:
1. Извлечение памяти — обновляет ChatSession.user_agent_profile (память о пользователе)
2. Детекция триггеров — создаёт PendingAction для проактивных сообщений
3. Глобальная биография — обновляет UserMemory.narrative_summary (только для AI Помощника)
4. Cron задача — проверяет "застывшие" чаты каждые 2 минуты
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import AsyncOpenAI
from loguru import logger
import json
import time
from services.audit_service import fire_and_forget_audit

from models import ChatSession, Message, UserMemory, PendingAction, ProactivitySettings, User, Agent
from config import settings as app_settings


# Инициализация OpenAI клиента
openai_client = AsyncOpenAI(api_key=app_settings.openai_api_key)


async def get_proactivity_settings(db: AsyncSession) -> ProactivitySettings:
    """Получить настройки проактивности (singleton)"""
    result = await db.execute(select(ProactivitySettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Создаём настройки по умолчанию
        settings = ProactivitySettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


async def get_new_messages(
    db: AsyncSession,
    session_id: int,
    last_summary_at: Optional[datetime]
) -> List[Message]:
    """
    Получить новые сообщения диалога для обновления памяти.
    Берём ВСЕ сообщения, созданные ПОСЛЕ последней суммаризации.
    Игнорируем is_archived, чтобы не потерять сжатые, но не обработанные сообщения.
    """
    query = select(Message).where(
        Message.session_id == session_id
    )
    
    if last_summary_at:
        query = query.where(Message.created_at > last_summary_at)
        
    query = query.order_by(Message.created_at)
    result = await db.execute(query)
    return result.scalars().all()


def format_messages_for_prompt(messages: List[Message]) -> str:
    """Форматировать сообщения для промпта"""
    formatted = []
    for msg in messages:
        role_name = "Пользователь" if msg.role.value == "user" else "AI"
        formatted.append(f"{role_name}: {msg.content}")
    return "\n".join(formatted)


async def process_memory_update(
    db: AsyncSession,
    chat_session: ChatSession,
    user: User,
    settings: ProactivitySettings
) -> None:
    """
    Только обновление памяти (Narrative Memory).
    Запускается каждые 2 часа (memory_update_interval).
    """
    # Получаем НОВЫЕ сообщения с момента последнего обновления
    new_messages = await get_new_messages(db, chat_session.id, chat_session.summarized_at)
    
    if not new_messages:
        return

    logger.info(f"🧠 Updating memory for session {chat_session.id} ({len(new_messages)} new msgs)")
    
    # 1. Получаем/Создаем глобальную память
    user_memory_result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == user.id)
    )
    user_memory = user_memory_result.scalar_one_or_none()
    
    if not user_memory and chat_session.agent_slug == "main_assistant":
        user_memory = UserMemory(user_id=user.id, narrative_summary="")
        db.add(user_memory)
        await db.commit()
        await db.refresh(user_memory)

    user_profile = user_memory.narrative_summary if user_memory else "Нет данных"
    current_memory = chat_session.user_agent_profile or "Пусто"
    
    # 2. Выбираем промпт и логику (Агент vs Ассистент)
    if chat_session.agent_slug == "main_assistant":
        # Логика AI Помощника (видит всех)
        all_sessions_result = await db.execute(
            select(ChatSession).where(ChatSession.user_id == user.id)
        )
        all_sessions = all_sessions_result.scalars().all()
        
        agent_memories = []
        for session in all_sessions:
            if session.user_agent_profile and session.id != chat_session.id:
                agent_result = await db.execute(select(Agent).where(Agent.slug == session.agent_slug))
                agent = agent_result.scalar_one_or_none()
                agent_name = agent.name if agent else session.agent_slug
                agent_memories.append(f"{agent_name}: {session.user_agent_profile}")
        
        all_agent_memories = "\n\n".join(agent_memories) if agent_memories else "Нет данных"
        
        prompt = settings.assistant_memory_prompt.format(
            full_chat_history=format_messages_for_prompt(new_messages), # Важно: только новые!
            current_memory=current_memory,
            user_profile=user_profile,
            all_agent_memories=all_agent_memories
        )
    else:
        # Логика обычного агента
        prompt = settings.agent_memory_prompt.format(
            full_chat_history=format_messages_for_prompt(new_messages),
            current_memory=current_memory,
            user_profile=user_profile
        )

    # 3. Запрос к LLM для памяти
    try:
        llm_messages = [
            {"role": "system", "content": "Ты — аналитик памяти. Точно следуй инструкциям. Верни валидный JSON."},
            {"role": "user", "content": prompt}
        ]
        
        # Call OpenAI
        response = await openai_client.chat.completions.create(
            model=settings.memory_model,
            messages=llm_messages,
            temperature=settings.memory_temperature,
            max_tokens=settings.memory_max_tokens
        )
        
        # Fire audit log
        if response.usage:
             # Extract cached_tokens if available
             cached_tokens = 0
             if hasattr(response.usage, 'prompt_tokens_details'):
                 details = response.usage.prompt_tokens_details
                 if hasattr(details, 'cached_tokens'):
                     cached_tokens = details.cached_tokens
             
             fire_and_forget_audit(
                 user_id=user.id,
                 agent_slug=f"{chat_session.agent_slug}:memory_update",
                 model=settings.memory_model,
                 messages=llm_messages,
                 response_content=response.choices[0].message.content or "",
                 input_tokens=response.usage.prompt_tokens,
                 output_tokens=response.usage.completion_tokens,
                 cached_tokens=cached_tokens,
                 duration_ms=0
             )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        result = json.loads(result_text)
        
        # 4. Сохраняем результаты
        memory_update = result.get("memory_update", current_memory)
        if isinstance(memory_update, (dict, list)):
            memory_update = json.dumps(memory_update, ensure_ascii=False)
            
        chat_session.user_agent_profile = memory_update
        chat_session.summarized_at = datetime.utcnow()
        
        if chat_session.agent_slug == "main_assistant":
            profile_update = result.get("global_profile_update", user_profile)
            if isinstance(profile_update, (dict, list)):
                profile_update = json.dumps(profile_update, ensure_ascii=False)
            if user_memory:
                 user_memory.narrative_summary = profile_update
                 user_memory.updated_at = datetime.utcnow()

        await db.commit()
        logger.info(f"✅ Memory updated for {chat_session.agent_slug}")

    except Exception as e:
        logger.error(f"❌ Error updating memory: {e}")


async def check_proactivity_trigger(
    db: AsyncSession,
    chat_session: ChatSession,
    user: User,
    settings: ProactivitySettings
) -> None:
    """
    Проверка на необходимость проактивного сообщения.
    Запускается отдельно, если прошло > 24 часов (proactivity_timeout).
    """
    logger.info(f"🤔 Checking proactivity for session {chat_session.id}")
    
    # 1. Получаем контекст
    user_memory_result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == user.id)
    )
    user_memory = user_memory_result.scalar_one_or_none()
    user_profile = user_memory.narrative_summary if user_memory and user_memory.narrative_summary else "Нет данных"
    agent_memory = chat_session.user_agent_profile or "Нет данных"
    
    # Вычисляем время молчания
    if chat_session.last_message_at:
        silence_duration = datetime.utcnow() - chat_session.last_message_at
        silence_hours = round(silence_duration.total_seconds() / 3600, 1)
    else:
        silence_hours = 0
    
    # Получаем последние сообщения для контекста
    recent_msgs = await db.execute(
        select(Message)
        .where(Message.session_id == chat_session.id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    
    # 2. Проверка Anti-Spam: лимит сообщений подряд
    max_consecutive = settings.max_consecutive_messages or 3
    consecutive_assistant_msgs = 0
    
    # recent_msgs уже отсортированы DESC (от новых к старым)
    # но нам нужно проверить их в этом порядке
    recent_msgs_list = recent_msgs.scalars().all()
    
    for msg in recent_msgs_list:
        if msg.role.value == "assistant":
            consecutive_assistant_msgs += 1
        else:
            # Прерываемся на первом сообщении пользователя
            break
            
    if consecutive_assistant_msgs >= max_consecutive:
        logger.info(f"🛑 Proactivity STOP: {consecutive_assistant_msgs} consecutive assistant messages (Limit: {max_consecutive})")
        # Обновляем timestamp проверки, чтобы не долбить этот чат постоянно, но не пишем
        chat_session.last_proactivity_check_at = datetime.utcnow()
        await db.commit()
        return

    full_chat_history = format_messages_for_prompt(list(reversed(recent_msgs_list)))
    
    # 3. Формируем промпт из настроек
    prompt = settings.proactivity_trigger_prompt.format(
        user_profile=user_profile,
        agent_memory=agent_memory,
        full_chat_history=full_chat_history,
        silence_hours=silence_hours
    )
    
    # 3. Запрос к LLM
    try:
        llm_messages = [{"role": "user", "content": prompt}]
        response = await openai_client.chat.completions.create(
            model=settings.trigger_model, 
            messages=llm_messages,
            temperature=settings.trigger_temperature,
            max_tokens=settings.trigger_max_tokens
        )
        
        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
             result_text = result_text.split("```")[1].replace("json", "").strip()
        
        result = json.loads(result_text)
        
        if result.get("create_task", False):
            topic = result.get("topic", "Возврат к теме")
            reason = f"Proactivity triggered after {silence_hours}h silence"
            
            # Проверяем Anti-Spam (уже есть pending?)
            existing = await db.scalar(
                select(PendingAction)
                .where(PendingAction.user_id == user.id)
                .where(PendingAction.agent_slug == chat_session.agent_slug)
                .where(PendingAction.status == "pending")
            )
            
            if not existing:
                action = PendingAction(
                    user_id=user.id,
                    agent_slug=chat_session.agent_slug,
                    topic_context=topic,
                    status="pending"
                )
                db.add(action)
                logger.info(f"🎯 Proactivity Triggered: {topic} ({reason})")
            else:
                 logger.info("⚠️ Proactivity skipped: Pending Action already exists")
        else:
            logger.info(f"💤 Proactivity decided not to act (create_task=false)")

        # Обновляем timestamp проверки
        chat_session.last_proactivity_check_at = datetime.utcnow()
        await db.commit()

    except Exception as e:
        logger.error(f"❌ Error checking proactivity: {e}")


async def process_idle_chat(
    db: AsyncSession,
    chat_session: ChatSession
) -> None:
    """
    Разделенная логика обработки:
    1. Память (каждые N часов)
    2. Проактивность (каждые M часов)
    """
    settings = await get_proactivity_settings(db)
    
    user = await db.scalar(select(User).where(User.id == chat_session.user_id))
    if not user: return
    
    now = datetime.utcnow()
    
    # === 1. Memory Update ===
    last_mem = chat_session.summarized_at or datetime.min
    if (now - last_mem) > timedelta(hours=settings.memory_update_interval):
        # Только если были сообщения с тех пор
        if chat_session.last_message_at and chat_session.last_message_at > last_mem:
            await process_memory_update(db, chat_session, user, settings)
            
     # === 2. Proactivity Check ===
    last_pro = chat_session.last_proactivity_check_at or datetime.min
    if (now - last_pro) > timedelta(hours=settings.proactivity_timeout):
        # 1. Проверяем, что чат реально молчит (а не только что говорили)
        # Тишина должна быть больше, чем таймаут
        if chat_session.last_message_at:
             silence_duration = now - chat_session.last_message_at
             if silence_duration > timedelta(hours=settings.proactivity_timeout):
                 
                 # 2. ОПТИМИЗАЦИЯ: Если мы уже проверяли этот диалог ПОСЛЕ последнего сообщения
                 # значит, мы уже решили ничего не делать. Не тратим токены повторно.
                 if chat_session.last_proactivity_check_at and chat_session.last_message_at:
                     if chat_session.last_proactivity_check_at > chat_session.last_message_at:
                         # logger.debug(f"Skipping proactivity for {chat_session.id}: already checked after last msg")
                         return

                 await check_proactivity_trigger(db, chat_session, user, settings)


async def check_idle_conversations(db: AsyncSession) -> None:
    """
    Cron: ищет чаты, требующие внимания.
    """
    # Для MVP берем чаты, где были сообщения за последние 7 дней
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Filter: Chats updated recently
    query = select(ChatSession).where(ChatSession.updated_at > week_ago)
    
    result = await db.execute(query)
    chats = result.scalars().all()
    
    for chat in chats:
        try:
            await process_idle_chat(db, chat)
        except Exception as e:
            logger.error(f"❌ Error processing chat {chat.id}: {e}")

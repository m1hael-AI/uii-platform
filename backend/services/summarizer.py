"""
Суммаризатор для проактивности AI University.

Компоненты:
1. Извлечение памяти — обновляет ChatSession.local_summary (память о пользователе)
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


async def get_all_messages(
    db: AsyncSession,
    session_id: int
) -> List[Message]:
    """Получить ВСЕ сообщения диалога"""
    query = select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    result = await db.execute(query)
    return result.scalars().all()


def format_messages_for_prompt(messages: List[Message]) -> str:
    """Форматировать сообщения для промпта"""
    formatted = []
    for msg in messages:
        role_name = "Пользователь" if msg.role.value == "user" else "AI"
        formatted.append(f"{role_name}: {msg.content}")
    return "\n".join(formatted)


async def process_agent_memory(
    db: AsyncSession,
    chat_session: ChatSession,
    user: User,
    settings: ProactivitySettings
) -> None:
    """
    Обработка памяти обычного агента:
    1. Извлечение фактов из диалога
    2. Обновление local_summary
    3. Детекция триггеров для проактивных задач
    """
    # Получаем ВСЮ историю диалога
    all_messages = await get_all_messages(db, chat_session.id)
    
    if not all_messages:
        return
    
    # Получаем биографию пользователя
    user_memory_result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == user.id)
    )
    user_memory = user_memory_result.scalar_one_or_none()
    user_profile = user_memory.narrative_summary if user_memory else "Нет данных"
    
    # Формируем промпт
    full_chat_history = format_messages_for_prompt(all_messages)
    current_memory = chat_session.local_summary or "Пусто"
    
    prompt = settings.agent_memory_prompt.format(
        full_chat_history=full_chat_history,
        current_memory=current_memory,
        user_profile=user_profile
    )
    
    # Генерируем обновление памяти
    try:
        response = await openai_client.chat.completions.create(
            model=settings.model,
            messages=[
                {"role": "system", "content": "Ты — аналитик диалогов. Извлекай важные факты о пользователе. Отвечай ТОЛЬКО валидным JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=settings.temperature,
            max_tokens=800
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Парсим JSON
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        result = json.loads(result_text)
        
        # Обновляем память
        chat_session.local_summary = result.get("memory_update", current_memory)
        chat_session.summarized_at = datetime.utcnow()
        
        logger.info(f"✅ Память агента обновлена: {chat_session.local_summary[:100]}...")
        
        # Проверяем триггер
        if result.get("create_task"):
            topic = result.get("topic", "Продолжение диалога")
            
            # Проверяем, нет ли уже pending задачи
            existing_action = await db.execute(
                select(PendingAction)
                .where(PendingAction.user_id == user.id)
                .where(PendingAction.agent_slug == chat_session.agent_slug)
                .where(PendingAction.status == "pending")
            )
            
            if not existing_action.scalar_one_or_none():
                pending_action = PendingAction(
                    user_id=user.id,
                    agent_slug=chat_session.agent_slug,
                    topic_context=topic,
                    status="pending"
                )
                db.add(pending_action)
                logger.info(f"🎯 Создана проактивная задача: agent={chat_session.agent_slug}, topic={topic}")
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки памяти агента: {e}")


async def process_assistant_memory(
    db: AsyncSession,
    chat_session: ChatSession,
    user: User,
    settings: ProactivitySettings
) -> None:
    """
    Обработка памяти AI Помощника:
    1. Извлечение фактов из диалога
    2. Обновление local_summary
    3. Обновление глобальной биографии (UserMemory.narrative_summary)
    4. Детекция триггеров
    """
    # Получаем ВСЮ историю диалога
    all_messages = await get_all_messages(db, chat_session.id)
    
    if not all_messages:
        return
    
    # Получаем биографию пользователя
    user_memory_result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == user.id)
    )
    user_memory = user_memory_result.scalar_one_or_none()
    
    if not user_memory:
        user_memory = UserMemory(user_id=user.id, narrative_summary="")
        db.add(user_memory)
        await db.commit()
        await db.refresh(user_memory)
    
    user_profile = user_memory.narrative_summary or "Нет данных"
    
    # Получаем все локальные памяти других агентов
    all_sessions_result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == user.id)
    )
    all_sessions = all_sessions_result.scalars().all()
    
    agent_memories = []
    for session in all_sessions:
        if session.local_summary and session.id != chat_session.id:
            # Получаем имя агента
            agent_result = await db.execute(
                select(Agent).where(Agent.slug == session.agent_slug)
            )
            agent = agent_result.scalar_one_or_none()
            agent_name = agent.name if agent else session.agent_slug
            agent_memories.append(f"{agent_name}: {session.local_summary}")
    
    all_agent_memories = "\n\n".join(agent_memories) if agent_memories else "Нет данных"
    
    # Формируем промпт
    full_chat_history = format_messages_for_prompt(all_messages)
    current_memory = chat_session.local_summary or "Пусто"
    
    prompt = settings.assistant_memory_prompt.format(
        full_chat_history=full_chat_history,
        current_memory=current_memory,
        user_profile=user_profile,
        all_agent_memories=all_agent_memories
    )
    
    # Генерируем обновление
    try:
        response = await openai_client.chat.completions.create(
            model=settings.model,
            messages=[
                {"role": "system", "content": "Ты — аналитик диалогов. Извлекай важные факты о пользователе и обновляй глобальный профиль. Отвечай ТОЛЬКО валидным JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=settings.temperature,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Парсим JSON
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        result = json.loads(result_text)
        
        # Обновляем локальную память AI Помощника
        chat_session.local_summary = result.get("memory_update", current_memory)
        chat_session.summarized_at = datetime.utcnow()
        
        # Обновляем глобальную биографию
        user_memory.narrative_summary = result.get("global_profile_update", user_profile)
        user_memory.updated_at = datetime.utcnow()
        
        logger.info(f"✅ Память AI Помощника обновлена")
        logger.info(f"✅ Глобальная биография обновлена: {user_memory.narrative_summary[:100]}...")
        
        # Проверяем триггер
        if result.get("create_task"):
            topic = result.get("topic", "Продолжение диалога")
            
            # Проверяем, нет ли уже pending задачи
            existing_action = await db.execute(
                select(PendingAction)
                .where(PendingAction.user_id == user.id)
                .where(PendingAction.agent_slug == chat_session.agent_slug)
                .where(PendingAction.status == "pending")
            )
            
            if not existing_action.scalar_one_or_none():
                pending_action = PendingAction(
                    user_id=user.id,
                    agent_slug=chat_session.agent_slug,
                    topic_context=topic,
                    status="pending"
                )
                db.add(pending_action)
                db.add(pending_action)
                logger.info(f"🎯 Создана проактивная задача для AI Помощника: topic={topic}")
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки памяти AI Помощника: {e}")


async def process_idle_chat(
    db: AsyncSession,
    chat_session: ChatSession
) -> None:
    """
    Обработка "застывшего" чата:
    - Для обычных агентов: извлечение памяти + детекция триггеров
    - Для AI Помощника: извлечение памяти + глобальная биография + детекция триггеров
    """
    settings = await get_proactivity_settings(db)
    
    # Получаем пользователя
    user_result = await db.execute(
        select(User).where(User.id == chat_session.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return
    
    print(f"📊 Обработка чата: user_id={user.id}, agent={chat_session.agent_slug}")
    
    # Проверяем, это AI Помощник или обычный агент
    if chat_session.agent_slug == "main_assistant":
        await process_assistant_memory(db, chat_session, user, settings)
    else:
        await process_agent_memory(db, chat_session, user, settings)


async def check_idle_conversations(db: AsyncSession) -> None:
    """
    Cron задача: проверяет "застывшие" чаты.
    Запускается каждые 2 минуты (настраивается в ProactivitySettings).
    """
    settings = await get_proactivity_settings(db)
    
    # Вычисляем порог времени
    idle_threshold = datetime.utcnow() - timedelta(minutes=settings.summarizer_idle_threshold)
    
    # Находим чаты, где:
    # 1. Последнее сообщение было > N минут назад
    # 2. Ещё не суммаризировали ИЛИ есть новые сообщения
    query = select(ChatSession).where(
        ChatSession.last_message_at < idle_threshold
    ).where(
        (ChatSession.summarized_at.is_(None)) |
        (ChatSession.summarized_at < ChatSession.last_message_at)
    )
    
    result = await db.execute(query)
    idle_chats = result.scalars().all()
    
    logger.info(f"🔍 Найдено {len(idle_chats)} застывших чатов")
    
    for chat in idle_chats:
        try:
            await process_idle_chat(db, chat)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки чата {chat.id}: {e}")
            continue
    
    logger.info(f"✅ Обработка завершена")

"""
Executor для проактивных сообщений AI University.

Компоненты:
1. Получение ВСЕЙ истории чата
2. Подстановка плейсхолдеров в промпт агента
3. Генерация проактивного сообщения через OpenAI
4. Сохранение в БД (Message)
5. Отправка в Telegram (если пользователь подключён)
6. Обновление статуса PendingAction
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import select
from openai import AsyncOpenAI
from loguru import logger

from models import (
    PendingAction, 
    ChatSession, 
    Message, 
    User, 
    Agent, 
    ProactivitySettings,
    UserMemory
)
from config import settings as app_settings


# Инициализация OpenAI клиента
openai_client = AsyncOpenAI(api_key=app_settings.openai_api_key)


async def get_all_chat_messages(db: AsyncSession, session_id: int) -> list[Message]:
    """Получить ВСЮ историю чата"""
    query = select(Message).where(
        Message.session_id == session_id
    ).order_by(Message.created_at.asc())
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_or_create_chat_session(
    db: AsyncSession,
    user_id: int,
    agent_slug: str
) -> ChatSession:
    """Получить или создать сессию чата"""
    query = select(ChatSession).where(
        ChatSession.user_id == user_id,
        ChatSession.agent_slug == agent_slug,
        ChatSession.is_active == True
    )
    
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    
    if not session:
        session = ChatSession(
            user_id=user_id,
            agent_slug=agent_slug,
            is_active=True,
            last_message_at=datetime.utcnow()
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
    
    return session


def format_chat_history(messages: list[Message]) -> str:
    """Форматировать историю чата для промпта"""
    if not messages:
        return "Нет предыдущих сообщений"
    
    formatted = []
    for msg in messages:
        role_name = "Пользователь" if msg.role.value == "user" else "AI"
        formatted.append(f"{role_name}: {msg.content}")
    
    return "\n".join(formatted)


def replace_placeholders(
    prompt: str,
    user: User,
    agent: Agent,
    user_memory: Optional[UserMemory],
    agent_summary: str,
    topic_context: str
) -> str:
    """
    Заменить плейсхолдеры в промпте агента.
    
    Доступные плейсхолдеры:
    - {user_name} — имя пользователя
    - {user_profile} — глобальная биография пользователя
    - {agent_summary} — локальная память агента о пользователе
    - {current_date} — текущая дата
    - {current_time} — текущее время
    - {topic_context} — тема для проактивного сообщения
    """
    now = datetime.utcnow()
    
    replacements = {
        "{user_name}": user.full_name or user.email.split("@")[0],
        "{user_profile}": user_memory.narrative_summary if user_memory else "Нет данных",
        "{agent_summary}": agent_summary or "Нет данных",
        "{current_date}": now.strftime("%Y-%m-%d"),
        "{current_time}": now.strftime("%H:%M"),
        "{topic_context}": topic_context
    }
    
    result = prompt
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    return result


async def generate_proactive_message(
    db: AsyncSession,
    agent: Agent,
    user: User,
    chat_history: str,
    topic_context: str,
    settings: ProactivitySettings
) -> str:
    """
    Генерировать проактивное сообщение через OpenAI.
    
    Логика:
    1. Берём промпт агента (agent.system_prompt)
    2. Заменяем плейсхолдеры
    3. Добавляем триггерное сообщение с темой
    4. Генерируем ответ
    """
    # Получаем память пользователя
    user_memory_result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == user.id)
    )
    user_memory = user_memory_result.scalar_one_or_none()
    
    # Получаем локальную память агента
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == user.id,
            ChatSession.agent_slug == agent.slug
        )
    )
    session = session_result.scalar_one_or_none()
    agent_summary = session.local_summary if session else ""
    
    # Заменяем плейсхолдеры в системном промпте
    system_prompt = replace_placeholders(
        agent.system_prompt,
        user,
        agent,
        user_memory,
        agent_summary,
        topic_context
    )
    
    # Формируем сообщения для OpenAI
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Добавляем историю чата (если есть)
    if chat_history and chat_history != "Нет предыдущих сообщений":
        # Парсим историю и добавляем в messages
        for line in chat_history.split("\n"):
            if line.startswith("Пользователь: "):
                messages.append({"role": "user", "content": line[14:]})
            elif line.startswith("AI: "):
                messages.append({"role": "assistant", "content": line[4:]})
    
    # Добавляем триггерное сообщение
    trigger_message = f"[ПРОАКТИВНОЕ СООБЩЕНИЕ] Тема: {topic_context}"
    messages.append({"role": "user", "content": trigger_message})
    
    # Генерируем ответ
    response = await openai_client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens
    )
    
    return response.choices[0].message.content.strip()


async def send_to_telegram(user: User, agent_name: str, message_text: str) -> None:
    """
    Отправить проактивное сообщение в Telegram.
    
    TODO: Реализовать отправку через Telegram Bot API
    """
    if not user.telegram_id:
        logger.warning(f"⚠️ Пользователь {user.id} не подключён к Telegram")
        return
    
    try:
        from bot.loader import bot
        
        text = f"💬 *{agent_name}*\n\n{message_text}"
        await bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            parse_mode="Markdown"
        )

        logger.info(f"✅ Сообщение отправлено в Telegram: user={user.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в Telegram: {e}")


async def execute_proactive_message(
    db: AsyncSession,
    action: PendingAction,
    settings: ProactivitySettings
) -> None:
    """
    Выполнить проактивное сообщение.
    
    Логика:
    1. Получить пользователя и агента
    2. Получить или создать сессию чата
    3. Получить ВСЮЮ историю чата
    4. Сгенерировать проактивное сообщение
    5. Сохранить в БД (2 сообщения: триггер + ответ)
    6. Отправить в Telegram
    7. Обновить статус PendingAction
    """
    try:
        # Получаем пользователя
        user_result = await db.execute(
            select(User).where(User.id == action.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.error(f"❌ Пользователь {action.user_id} не найден")
            action.status = "failed"
            await db.commit()
            return
        
        # Получаем агента
        agent_result = await db.execute(
            select(Agent).where(Agent.slug == action.agent_slug)
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            logger.error(f"❌ Агент {action.agent_slug} не найден")
            action.status = "failed"
            await db.commit()
            return
        
        # Получаем или создаём сессию чата
        session = await get_or_create_chat_session(db, user.id, agent.slug)
        
        # Получаем ВСЮ историю чата
        all_messages = await get_all_chat_messages(db, session.id)
        chat_history = format_chat_history(all_messages)
        
        logger.info(f"📝 Генерация проактивного сообщения: user={user.id}, agent={agent.slug}")
        
        # Генерируем проактивное сообщение
        proactive_text = await generate_proactive_message(
            db,
            agent,
            user,
            chat_history,
            action.topic_context,
            settings
        )
        
        # Сохраняем триггерное сообщение (от системы)
        trigger_message = Message(
            session_id=session.id,
            role="user",
            content=f"[ПРОАКТИВНОЕ] {action.topic_context}",
            created_at=datetime.utcnow()
        )
        db.add(trigger_message)
        
        # Сохраняем ответ агента
        response_message = Message(
            session_id=session.id,
            role="assistant",
            content=proactive_text,
            created_at=datetime.utcnow()
        )
        db.add(response_message)
        
        # Обновляем last_message_at
        session.last_message_at = datetime.utcnow()
        
        # Обновляем статус задачи
        action.status = "sent"
        action.sent_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"✅ Проактивное сообщение сохранено в БД")
        
        # Отправляем в Telegram
        await send_to_telegram(user, agent.name, proactive_text)
        
        logger.info(f"🎉 Проактивное сообщение успешно отправлено!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения проактивного сообщения: {e}")
        action.status = "failed"
        await db.commit()
        raise

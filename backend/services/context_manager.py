from typing import List, Dict, Any
from loguru import logger
from utils.token_counter import count_tokens_from_messages_async, count_string_tokens

# Лимиты контекста для моделей (Token Context Window) - Data 2026
MODEL_LIMITS = {
    # GPT-4.1 Family
    "gpt-4.1": 1000000,
    "gpt-4.1-mini": 1000000,

    # GPT-5 Family
    "gpt-5": 272000,
    "gpt-5-mini": 400000,

    # Legacy / Stable
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
}

DEFAULT_LIMIT = 128000

def get_model_limit(model: str) -> int:
    """Возвращает лимит токенов для модели или дефолтное значение"""
    return MODEL_LIMITS.get(model, DEFAULT_LIMIT)

async def is_context_overflow(
    messages: List[Dict[str, Any]], 
    max_tokens: int = 0, # 0 = use model limit
    threshold: float = 0.9, # Default to 90% as requested
    model: str = "gpt-4o"
) -> bool:
    """
    Проверяет, превышен ли "мягкий" лимит контекста.
    Если max_tokens=0, берет лимит из базы знаний о моделях.
    
    Threshold 0.9 означает, что если занято > 90% окна, возвращаем True.
    """
    limit = max_tokens
    if limit <= 0:
        limit = get_model_limit(model)
        
    soft_limit = limit * threshold
    
    # Use Async Token Counter to prevent blocking main loop
    total_tokens = await count_tokens_from_messages_async(messages, model)
    
    # DEBUG: Always log the check
    logger.info(f"🔍 Context Check: {total_tokens} tokens | Soft Limit: {int(soft_limit)} ({threshold*100}% of {limit}) | Model: {model}")
    
    if total_tokens > soft_limit:
        logger.info(f"⚠️ Context Overflow: {total_tokens}/{limit} tokens (Threshold: {int(soft_limit)})")
        return True
    
    logger.info(f"✅ Context OK: {total_tokens} < {int(soft_limit)}")    
    return False


# === Logic for Compression ===

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from models import Message, MessageRole, ChatSession
from services.openai_service import generate_chat_response
from database import async_engine
from sqlalchemy.orm import sessionmaker

# Factory for creating independent sessions in background tasks
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def compress_context_task(
    session_id: int, 
    keep_last_n: int = 20,
    model: str = "gpt-4o"
):
    """
    Фоновая задача для технического сжатия истории (Context Compression / Summarization).
    Запускается при переполнении контекста (Context Overflow).
    Создает СОБСТВЕННУЮ сессию БД.
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"🧹 Starting context compression for session {session_id}...")
            
            # Получаем настройки сжатия из ChatSettings
            from services.settings_service import get_chat_settings
            chat_settings = await get_chat_settings(db)
            
            # 1. Получаем сообщения (только НЕ архивные)
            query = select(Message).where(
                Message.session_id == session_id,
                Message.is_archived == False  # Берём только актуальные
            ).order_by(Message.created_at.asc())
            result = await db.execute(query)
            all_messages = result.scalars().all()
        
            if len(all_messages) <= keep_last_n:
                 logger.info(f"Skipping compression: not enough messages ({len(all_messages)} <= {keep_last_n})")
                 return
    
            # Определяем сообщения для сжатия (всё, кроме последних N)
            # Если первое сообщение уже является саммари (мы это поймем по маркеру), то включаем и его
            messages_to_compress = all_messages[:-keep_last_n]
            messages_to_keep = all_messages[-keep_last_n:]
            
            if not messages_to_compress:
                return
    
            logger.info(f"Compressing {len(messages_to_compress)} messages...")
    
            # Формируем текст для саммаризатора
            previous_summary = "Нет предыдущего саммари."
            text_to_compress = ""
            
            for msg in messages_to_compress:
                role = "AI" if msg.role == MessageRole.ASSISTANT else "User"
                
                # Check for existing summary in the first message(s)
                if msg.role == MessageRole.SYSTEM and "[SUMMARY]" in msg.content:
                     # Extract content after standard prefix or take whole content
                     content = msg.content
                     prefix = "[SUMMARY] Краткое содержание предыдущего разговора:\n"
                     if prefix in content:
                         previous_summary = content.replace(prefix, "")
                     else:
                         previous_summary = content
                     continue
                
                text_to_compress += f"{role}: {msg.content}\n"
    
            if not text_to_compress.strip():
                return
    
            # 2. Запрос к LLM
            # Получаем промпт из ProactivitySettings
            from models import ProactivitySettings
            proactivity_settings_result = await db.execute(select(ProactivitySettings))
            proactivity_settings = proactivity_settings_result.scalar_one_or_none()

            if not proactivity_settings or not proactivity_settings.compression_prompt:
                logger.error("❌ ProactivitySettings or compression_prompt missing in DB! Cannot compress context.")
                return

            prompt_template = proactivity_settings.compression_prompt

            # Format the prompt with both parts
            try:
                prompt = prompt_template.format(
                    previous_summary=previous_summary,
                    text_to_compress=text_to_compress
                )
            except KeyError:
                logger.error("❌ Prompt format mismatch in compression! The prompt in DB doesn't match the code variables.")
                return
    
            new_summary_text = await generate_chat_response(
                messages=[{"role": "user", "content": prompt}],
                model=chat_settings.compression_model,  # Используем модель для сжатия из настроек
                temperature=chat_settings.compression_temperature,  # Используем температуру для сжатия
                max_tokens=chat_settings.compression_max_tokens  # Используем max_tokens для сжатия (может быть None)
            )
            
            final_summary_content = f"[SUMMARY] Краткое содержание предыдущего разговора:\n{new_summary_text}"
            
            # 3. Транзакция обновления БД
            # Вместо удаления делаем Soft Delete (архивацию)
            ids_to_archive = [m.id for m in messages_to_compress]
            
            # ВАЖНО: Обновляем статус is_archived = True
            await db.execute(
                update(Message)
                .where(Message.id.in_(ids_to_archive))
                .values(is_archived=True)
            )
            
            # Создаем новое сообщение-саммари и вставляем его "в прошлое" 
            # (ставим время чуть раньше первого сохраненного сообщения)
            first_kept_msg_time = messages_to_keep[0].created_at if messages_to_keep else datetime.utcnow()
            summary_time = first_kept_msg_time  # Или slightly before
            
            summary_msg = Message(
                session_id=session_id,
                role=MessageRole.SYSTEM, # System роль идеально подходит для контекста
                content=final_summary_content,
                created_at=summary_time # Технически порядок ID может сбиться, но сортировка по времени спасет
            )
            db.add(summary_msg)
            
            await db.commit()
            logger.info(f"✅ Context compressed. Archived {len(ids_to_archive)} msgs. New summary length: {len(final_summary_content)}")
            
        except Exception as e:
            logger.error(f"❌ Error during context compression: {e}")
            # Не рейзим ошибку, чтобы не класть основной процесс, если это вызовется синхронно (хотя мы будем вызывать в фоне)

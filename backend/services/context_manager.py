from typing import List, Dict, Any
from loguru import logger
from utils.token_counter import count_tokens_from_messages, count_string_tokens

# Лимиты контекста для моделей (Token Context Window) - Data 2026

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

def is_context_overflow(
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
    total_tokens = count_tokens_from_messages(messages, model)
    
    # DEBUG: Always log the check
    logger.info(f"🔍 Context Check: {total_tokens} tokens | Soft Limit: {int(soft_limit)} ({threshold*100}% of {limit}) | Model: {model}")
    
    if total_tokens > soft_limit:
        logger.info(f"⚠️ Context Overflow: {total_tokens}/{limit} tokens (Threshold: {int(soft_limit)})")
        return True
    
    logger.info(f"✅ Context OK: {total_tokens} < {int(soft_limit)}")    
    return False


# === Logic for Compression ===

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
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
    Фоновая задача для сжатия истории диалога.
    Создает СОБСТВЕННУЮ сессию БД.
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"🧹 Starting context compression for session {session_id}...")
            
            # 1. Получаем сообщения
            query = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
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
            text_to_compress = ""
            user_name_heuristic = "User"
            
            for msg in messages_to_compress:
                role = "AI" if msg.role == MessageRole.ASSISTANT else "User"
                if msg.role == MessageRole.SYSTEM and "[SUMMARY]" in msg.content:
                     text_to_compress += f"ПРЕДЫДУЩЕЕ КРАТКОЕ СОДЕРЖАНИЕ:\n{msg.content}\n\n"
                     continue
                
                text_to_compress += f"{role}: {msg.content}\n"
    
            if not text_to_compress.strip():
                return
    
            # 2. Запрос к LLM
            prompt = (
                f"Ниже приведен фрагмент диалога между пользователем и AI-ассистентом.\n"
                f"Твоя задача — создать ПОДРОБНОЕ структурированное саммари этого диалога.\n\n"
                f"ТРЕБОВАНИЯ:\n"
                f"1. Перечисли ВСЕ основные темы, которые обсуждались\n"
                f"2. Сохрани ключевые вопросы пользователя и ответы AI\n"
                f"3. Укажи важные факты, имена, даты, технические термины\n"
                f"4. Структурируй по темам (используй маркеры или нумерацию)\n"
                f"5. Игнорируй только приветствия и общие фразы\n"
                f"6. Саммари должно быть достаточно детальным, чтобы AI мог продолжить разговор без потери контекста\n\n"
                f"=== ДИАЛОГ ===\n"
                f"{text_to_compress[:100000]}\n" # Hard limit safety
                f"=== КОНЕЦ ДИАЛОГА ===\n\n"
                f"Создай подробное структурированное саммари:"
            )
    
            new_summary_text = await generate_chat_response(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4.1-mini", # Дешевая модель для сжатия
                temperature=0.2 # Низкая температура для точности
                # max_tokens НЕ указываем — саммари может быть любого размера
            )
            
            final_summary_content = f"[SUMMARY] Краткое содержание предыдущего разговора:\n{new_summary_text}"
            
            # 3. Транзакция обновления БД
            # Удаляем сжатые сообщения
            ids_to_delete = [m.id for m in messages_to_compress]
            
            # Проверяем, было ли у нас уже сообщение-саммари в начале?
            # Если да, мы его удаляем вместе со всеми и создаем новое. 
            # Или, если мы хотим сохранить ID, обновляем. 
            # Проще: удалить всё старое, создать новое первое сообщение.
            
            # ВАЖНО: Удаляем аккуратно
            await db.execute(delete(Message).where(Message.id.in_(ids_to_delete)))
            
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
            logger.info(f"✅ Context compressed. Deleted {len(ids_to_delete)} msgs. New summary length: {len(final_summary_content)}")
            
        except Exception as e:
            logger.error(f"❌ Error during context compression: {e}")
            # Не рейзим ошибку, чтобы не класть основной процесс, если это вызовется синхронно (хотя мы будем вызывать в фоне)

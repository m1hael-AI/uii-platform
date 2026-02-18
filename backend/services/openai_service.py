"""
Сервис для работы с OpenAI API.
Использует AsyncOpenAI для неблокирующих запросов.
Vendor-agnostic: стандартный SDK, без привязки к платформе.
"""

from typing import AsyncGenerator, List, Dict, Optional
from openai import AsyncOpenAI
from config import settings
from services.audit_service import fire_and_forget_audit
import time
import json
import re
import logging

logger = logging.getLogger(__name__)


# Инициализация асинхронного клиента OpenAI
# Использует стандартную переменную OPENAI_API_KEY из окружения
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_chat_response(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    user_id: Optional[int] = None,
    agent_slug: str = "unknown"
) -> str:
    """
    Генерирует ответ от AI агента (без стриминга).
    
    Args:
        messages: История сообщений в формате OpenAI
        model: Модель для использования (по умолчанию из конфига)
        temperature: Температура генерации
        max_tokens: Максимальное количество токенов
    
    Returns:
        Текст ответа от AI
    """
    start_time = time.time()
    response = await client.chat.completions.create(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    content = response.choices[0].message.content or ""
    
    # Audit Log
    if user_id and response.usage:
        duration = int((time.time() - start_time) * 1000)
        
        # Extract Real Token Usage from API
        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        
        cached_tokens = 0
        if getattr(usage, "prompt_tokens_details", None):
             cached_tokens = usage.prompt_tokens_details.cached_tokens or 0
        
        target_model = model or settings.openai_model
        
        fire_and_forget_audit(
            user_id=user_id,
            agent_slug=agent_slug,
            model=target_model,
            messages=messages,
            response_content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            duration_ms=duration
        )
        
    return content


async def generate_embedding(
    text: str,
    model: str = "text-embedding-3-small"
) -> List[float]:
    """
    Генерирует вектор для текста (Embedding).
    
    Args:
        text: Текст для векторизации
        model: Модель эмбеддингов (по умолчанию text-embedding-3-small)
        
    Returns:
        List[float]: Вектор (массив чисел)
    """
    # Replace newlines to avoid issues with some older models, 
    # though 3-small is robust, it's a good practice.
    text = text.replace("\n", " ")
    
    response = await client.embeddings.create(
        input=[text],
        model=model
    )
    
    return response.data[0].embedding


async def stream_chat_response(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    user_id: Optional[int] = None,
    agent_slug: str = "unknown"
) -> AsyncGenerator[str, None]:
    """
    Генерирует ответ от AI агента со стримингом.
    Используется для WebSocket соединений.
    
    Args:
        messages: История сообщений в формате OpenAI
        model: Модель для использования
        temperature: Температура генерации
        max_tokens: Максимальное количество токенов
    
    Yields:
        Куски текста по мере генерации
    """
    start_time = time.time()
    accumulated_content = ""
    
    # Request stream with Usage stats
    stream = await client.chat.completions.create(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        stream_options={"include_usage": True},
    )
    
    usage_data = None
    
    async for chunk in stream:
        if chunk.choices:
            delta = chunk.choices[0].delta.content
            if delta:
                accumulated_content += delta
                yield delta
        
        if chunk.usage:
            usage_data = chunk.usage

    # Audit Log
    if user_id and usage_data:
        duration = int((time.time() - start_time) * 1000)
        
        input_tokens = usage_data.prompt_tokens
        output_tokens = usage_data.completion_tokens
        
        cached_tokens = 0
        if getattr(usage_data, "prompt_tokens_details", None):
             cached_tokens = usage_data.prompt_tokens_details.cached_tokens or 0
        
        target_model = model or settings.openai_model
        
        fire_and_forget_audit(
            user_id=user_id,
            agent_slug=agent_slug,
            model=target_model,
            messages=messages,
            response_content=accumulated_content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            duration_ms=duration
        )


async def summarize_conversation(
    conversation_history: List[Dict[str, str]],
    existing_summary: str = "",
    judge_prompt: str = "",
    user_id: Optional[int] = None,
) -> Dict[str, str]:
    """
    Анализирует диалог и обновляет профиль пользователя.
    """
    system_message = judge_prompt or """
    Ты — анализатор диалогов образовательной платформы.
    Твоя задача:
    1. Обновить нарративное резюме о пользователе
    2. Выявить темы, которые могут заинтересовать других AI-агентов
    
    Верни JSON с полями:
    - updated_summary: обновлённое резюме
    - potential_topics: массив тем для других агентов
    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"Текущее резюме:\n{existing_summary}\n\nНовый диалог:\n{str(conversation_history)}"},
    ]
    
    start_time = time.time()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.3,
        max_tokens=1500,
    )
    
    # Audit Log
    if user_id and response.usage:
        duration = int((time.time() - start_time) * 1000)
        
        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        cached_tokens = 0
        if getattr(usage, "prompt_tokens_details", None):
             cached_tokens = usage.prompt_tokens_details.cached_tokens or 0
        
        fire_and_forget_audit(
            user_id=user_id,
            agent_slug="system_summarizer",
            model=settings.openai_model,
            messages=messages,
            response_content=response.choices[0].message.content or "",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            duration_ms=duration
        )
    
    # Парсим ответ
    content = response.choices[0].message.content or "{}"
    
    parsed_data = {}
    try:
        # Попытка найти JSON объект в ответе (обработка markdown блоков ```json ... ```)
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed_data = json.loads(json_str)
        else:
            logger.warning(f"Could not find JSON in response for user {user_id}")
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON for user {user_id}: {e}. Content: {content[:100]}...")
    
    # Извлекаем данные с фоллбэком на старые значения
    updated_summary = parsed_data.get("updated_summary", existing_summary)
    potential_topics = parsed_data.get("potential_topics", [])
    
    return {
        "raw_response": content,
        "updated_summary": updated_summary,
        "potential_topics": potential_topics,
    }

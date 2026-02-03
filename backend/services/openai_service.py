"""
Сервис для работы с OpenAI API.
Использует AsyncOpenAI для неблокирующих запросов.
Vendor-agnostic: стандартный SDK, без привязки к платформе.
"""

from typing import AsyncGenerator, List, Dict, Optional
from openai import AsyncOpenAI
from config import settings


# Инициализация асинхронного клиента OpenAI
# Использует стандартную переменную OPENAI_API_KEY из окружения
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_chat_response(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
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
    response = await client.chat.completions.create(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    return response.choices[0].message.content or ""


async def stream_chat_response(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
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
    stream = await client.chat.completions.create(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def summarize_conversation(
    conversation_history: List[Dict[str, str]],
    existing_summary: str = "",
    judge_prompt: str = "",
) -> Dict[str, str]:
    """
    Анализирует диалог и обновляет профиль пользователя.
    Используется Summarizer'ом (Judge) для проактивности.
    
    Args:
        conversation_history: История диалога
        existing_summary: Текущее резюме пользователя
        judge_prompt: Системный промпт для анализа (из SystemConfig)
    
    Returns:
        Словарь с обновлённым summary и списком тем для других агентов
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
    
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.3,
        max_tokens=1500,
    )
    
    # Парсим ответ (в реальности нужен более надёжный парсинг)
    content = response.choices[0].message.content or "{}"
    
    return {
        "raw_response": content,
        "updated_summary": existing_summary,  # TODO: Парсить JSON
        "potential_topics": [],
    }

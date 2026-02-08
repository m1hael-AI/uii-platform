import tiktoken
from typing import List, Dict, Any
from loguru import logger

# Кэш энкодеров, чтобы не загружать их каждый раз
encodings = {}

def get_encoding(model: str = "gpt-4o"):
    """Получить энкодер для модели"""
    if model not in encodings:
        try:
            logger.info(f"⏳ Loading tiktoken encoding for {model}...")
            import time
            t0 = time.time()
            encodings[model] = tiktoken.encoding_for_model(model)
            logger.info(f"✅ Tiktoken loaded in {time.time() - t0:.2f}s")
        except KeyError:
            # Fallback для новых/неизвестных моделей
            logger.warning(f"Модель {model} не найдена в tiktoken, используем cl100k_base")
            encodings[model] = tiktoken.get_encoding("cl100k_base")
    return encodings[model]

def count_tokens_from_messages(messages: List[Dict[str, Any]], model: str = "gpt-4o") -> int:
    """
    Подсчет токенов для списка сообщений (формат ChatML).
    Основано на официальной документации OpenAI.
    """
    if not messages:
        return 0
        
    try:
        encoding = get_encoding(model)
        
        tokens_per_message = 3
        tokens_per_name = 1
        
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                if not isinstance(value, str):
                    continue
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
                    
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens
    except Exception as e:
        logger.error(f"Error counting input tokens: {e}")
        return len(str(messages)) // 4 # Fallback

def count_string_tokens(text: str, model: str = "gpt-4o") -> int:
    """Подсчет токенов для простой строки"""
    if not text:
        return 0
    try:
        encoding = get_encoding(model)
        return len(encoding.encode(text))
    except Exception as e:
         logger.error(f"Error counting string tokens: {e}")
         return len(text) // 4

import asyncio
from functools import partial

async def count_tokens_from_messages_async(messages: List[Dict[str, Any]], model: str = "gpt-4o") -> int:
    """Асинхронная обертка для подсчета токенов сообщений (в пуле потоков)"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(count_tokens_from_messages, messages, model))

async def count_string_tokens_async(text: str, model: str = "gpt-4o") -> int:
    """Асинхронная обертка для подсчета токенов строки (в пуле потоков)"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(count_string_tokens, text, model))

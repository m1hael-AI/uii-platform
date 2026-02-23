import json
from loguru import logger
from datetime import datetime, timedelta
from sqlalchemy import update
from database import async_session_factory
from models import LLMAudit
import asyncio

# Цены (Standard Tier per 1M tokens)
# Input / Cached Input / Output
PRICES = {
    "gpt-4o":        {"input": 2.50, "cached_input": 1.25,  "output": 10.00},
    "gpt-4o-mini":   {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4.1-mini":  {"input": 0.40, "cached_input": 0.10,  "output": 1.60},
    # Fallbacks / Legacy
    "gpt-3.5-turbo": {"input": 0.50, "cached_input": 0.50,  "output": 1.50},
    "gpt-4o-2024-05-13": {"input": 5.00, "cached_input": 5.00, "output": 15.00},
    # Perplexity (OpenRouter)
    "perplexity/sonar-reasoning-pro": {"input": 2.00, "cached_input": 2.00, "output": 8.00},
    "perplexity/sonar-pro": {"input": 3.00, "cached_input": 3.00, "output": 15.00},
    "perplexity/sonar": {"input": 1.00, "cached_input": 1.00, "output": 1.00},
}

async def log_llm_interaction(
    user_id: int,
    agent_slug: str,
    model: str,
    messages: list,
    response_content: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    duration_ms: int = 0,
    status: str = "success",
    error: str = None,
    cost_usd_api: float = None  # Точная стоимость из API (OpenRouter). Если None — считаем локально.
):
    """
    Асинхронно записывает лог обращения к LLM с точным расчетом стоимости.
    Если cost_usd_api передан (из OpenRouter) — используем его напрямую.
    Иначе — считаем по таблице PRICES (для OpenAI).
    """
    try:
        if cost_usd_api is not None:
            # Точная стоимость из ответа API (OpenRouter передаёт usage.cost)
            cost = cost_usd_api
        else:
            # Считаем локально по таблице цен
            price = PRICES.get(model, PRICES["gpt-4o-mini"])  # Fallback to mini
            regular_input_tokens = max(0, input_tokens - cached_tokens)
            cost = (
                (regular_input_tokens / 1_000_000 * price["input"]) +
                (cached_tokens / 1_000_000 * price["cached_input"]) +
                (output_tokens / 1_000_000 * price["output"])
            )
        
        audit_entry = LLMAudit(
            user_id=user_id,
            agent_slug=agent_slug,
            model=model,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=round(cost, 9), # More precision for micro-costs
            duration_ms=duration_ms,
            request_json=json.dumps(messages, ensure_ascii=False),
            response_json=response_content if response_content else "",
            status=status,
            error_message=error,
            created_at=datetime.utcnow()
        )
        
        async with async_session_factory() as session:
            session.add(audit_entry)
            await session.commit()
            
    except Exception as e:
        logger.error(f"❌ Failed to write Audit Log: {e}")

def fire_and_forget_audit(*args, **kwargs):
    """
    Запускает логирование в фоне, не блокируя основной поток.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(log_llm_interaction(*args, **kwargs))
    except RuntimeError:
        # Если нет цикла событий (редкий кейс, но бывает)
        pass

async def cleanup_old_logs(days: int = 7):
    """
    Очищает тексты логов старше N дней, оставляя метаданные (токены, стоимость).
    To be called by a scheduler or cron.
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with async_session_factory() as session:
            stmt = (
                update(LLMAudit)
                .where(LLMAudit.created_at < cutoff_date)
                .values(request_json="", response_json="", status="cleaned")
            )
            await session.execute(stmt)
            await session.commit()
            # logger.info(f"🧹 Cleaned up LLM logs older than {days} days")
    except Exception as e:
        logger.error(f"Error cleaning logs: {e}")

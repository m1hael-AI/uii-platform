import os
import yaml
import json
from loguru import logger
import asyncio
import time
import httpx
from sqlalchemy import select
from database import async_session_factory
from models import NewsSettings
from services.audit_service import fire_and_forget_audit
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ValidationError
from config import settings



# --- Response Schemas ---

class NewsItemSchema(BaseModel):
    title: str = Field(description="Заголовок новости")
    summary: str = Field(description="Краткое описание")
    source_url: str = Field(description="URL источника")
    published_at: str = Field(description="Дата публикации ISO")
    tags: List[str] = Field(default_factory=list, description="Теги")

class HarvesterResponse(BaseModel):
    news: List[NewsItemSchema]

class WriterResponse(BaseModel):
    title: str
    content: str
    key_points: List[str] = Field(default_factory=list)

class PerplexityImage(BaseModel):
    imageUrl: Optional[str] = None
    originUrl: Optional[str] = None
    height: Optional[int] = None
    width: Optional[int] = None

# --- Client ---

class PerplexityClient:
    """
    Клиент для взаимодействия с Perplexity через OpenRouter.
    Реализует Harvester (поиск) и Writer (генерация).
    """
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = settings.perplexity_model
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://ai-university.app",
            "X-Title": "AI University",
            "Content-Type": "application/json"
        }

    async def _get_settings(self) -> NewsSettings:
        """Fetch current settings from DB"""
        async with async_session_factory() as db:
            result = await db.execute(select(NewsSettings).limit(1))
            settings_db = result.scalar_one_or_none()
            if not settings_db:
                # Return default mock if not found (should be seeded)
                return NewsSettings()
            return settings_db



    async def _request(self, messages: List[Dict], response_model: Any, retries: int = 3) -> Optional[Any]:
        """
        Выполняет запрос к API с ретраями и валидацией JSON.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(retries):
                start_time = time.time()
                try:
                    schema = response_model.model_json_schema()
                    
                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": response_model.__name__,
                                "strict": True,
                                "schema": schema
                            }
                        },
                        "temperature": 0.1
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=payload
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"API Error {response.status_code}: {response.text}")
                        # Если 429 (Rate Limit) - ждем
                        if response.status_code == 429:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        # Если 4xx (Client Error) кроме 429 - выходим
                        if 400 <= response.status_code < 500:
                            return None
                        raise httpx.HTTPStatusError(message="Server Error", request=response.request, response=response)

                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    
                    # Audit Log
                    try:
                        usage = data.get('usage', {})
                        input_tokens = usage.get('prompt_tokens', 0)
                        output_tokens = usage.get('completion_tokens', 0)
                        duration = int((time.time() - start_time) * 1000)
                        cost_usd_api = usage.get('cost')  # OpenRouter возвращает точную цену
                        
                        fire_and_forget_audit(
                            user_id=0, # System
                            agent_slug="news_agent",
                            model=self.model,
                            messages=messages,
                            response_content=content,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            duration_ms=duration,
                            cost_usd_api=cost_usd_api
                        )
                    except Exception as audit_err:
                        logger.error(f"Audit Log Failed: {audit_err}")

                    # Пытаемся распарсить JSON
                    try:
                        json_obj = json.loads(content)
                        # Валидируем Pydantic моделью
                        return response_model.model_validate(json_obj)
                    except (json.JSONDecodeError, ValidationError) as e:
                        logger.error(f"JSON Parsing Error: {e}. Content: {content[:100]}...")
                        # Ретрай, если модель вернула битый JSON
                        continue
                        
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                    if attempt == retries - 1:
                        logger.error("Max retries reached")
                        return None
                    await asyncio.sleep(2 ** attempt)
        return None

    async def search_news(self, query: str = None, context: str = None, exclude_titles: List[str] = None) -> List[NewsItemSchema]:
        """
        HARVESTER: Ищет новости.
        Если query задан - ищет по теме (User Search).
        Если query нет - ищет главные новости за сутки (Nightly Worker).
        """
        settings_db = await self._get_settings()
        
        user_content = f"Date: {asyncio.get_event_loop().time()}" 
        
        if query:
            raw_prompt = settings_db.harvester_search_prompt
            # Replace placeholders safely
            system_prompt = raw_prompt.replace("{query}", query)
            if context:
                if "{context}" in system_prompt:
                    system_prompt = system_prompt.replace("{context}", context)
                else:
                    # Fallback: Append context if placeholder missing
                    system_prompt += f"\n\n=== CONTEXT (ALREADY KNOWN) ===\n{context}"
            else:
                system_prompt = system_prompt.replace("{context}", "No known news.")
            
            user_content = f"Topic: {query}. Find fresh news."
            if exclude_titles:
                user_content += f"\nEXCLUDE these known news: {', '.join(exclude_titles[:5])}..."
        else:
            system_prompt = settings_db.harvester_nightly_prompt
            user_content = "Find top AI news for the last 24 hours."

        # Inject Tag Instructions
        tag_instruction = f"\n\n=== TAGS INSTRUCTION ===\nAssign 1-3 tags to each news item.\nChoose ONLY from this allowed list: {settings_db.allowed_tags}.\nDO NOT invent new tags. If nothing fits, use 'General AI'."
        system_prompt += tag_instruction

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # Добавляем параметр recency_filter в payload? 
        # OpenRouter не всегда пробрасывает параметры Perplexity, но 'sonar-pro' обычно понимает промпт.
        # Однако `search_recency_filter` это параметр API Perplexity. 
        # В OpenRouter это передается через `provider` settings или просто надеемся на модель.
        # Для Sonar-Pro (онлайновый) лучше писать в промпт "Last 24 hours".
        
        result: Optional[HarvesterResponse] = await self._request(messages, HarvesterResponse)
        if result:
            return result.news
        return []

    async def generate_article(self, news_item: NewsItemSchema) -> Tuple[Optional[WriterResponse], List[str], Optional[str]]:
        """
        WRITER: Пишет статью по заголовку и ссылкам.
        Возвращает: (WriterResponse, citations) — citations это список URL из Perplexity.
        """
        settings_db = await self._get_settings()
        system_prompt = settings_db.writer_prompt
        
        user_content = f"""
        WRITE ARTICLE BASED ON:
        Title: {news_item.title}
        Summary: {news_item.summary}
        Source URL: {news_item.source_url}
        Published: {news_item.published_at}
        
        Verify facts using the source URL if possible.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # Делаем запрос напрямую (не через _request), чтобы получить citations
        retries = 3
        async with httpx.AsyncClient(timeout=90.0) as client:
            for attempt in range(retries):
                start_time = time.time()
                try:
                    schema = WriterResponse.model_json_schema()
                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": WriterResponse.__name__,
                                "strict": True,
                                "schema": schema
                            }
                        },
                        "temperature": 0.1
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=payload
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Writer API Error {response.status_code}: {response.text}")
                        if response.status_code == 429:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        if 400 <= response.status_code < 500:
                            return None, [], None
                        raise httpx.HTTPStatusError(message="Server Error", request=response.request, response=response)

                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    
                    # Извлекаем citations (список URL от Perplexity)
                    citations: List[str] = data.get('citations', [])
                    
                    # Извлекаем первую картинку из блока images
                    image_url: Optional[str] = None
                    images_raw = data.get('images', [])
                    logger.info(f"📷 Perplexity images_raw (count={len(images_raw)}): {str(images_raw)[:300]}")
                    if images_raw and isinstance(images_raw, list):
                        first = images_raw[0]
                        if isinstance(first, dict):
                            image_url = first.get('imageUrl') or first.get('image_url')
                        elif isinstance(first, str):
                            image_url = first  # на случай если вернули просто URL строкой
                    
                    # Audit Log
                    try:
                        usage = data.get('usage', {})
                        input_tokens = usage.get('prompt_tokens', 0)
                        output_tokens = usage.get('completion_tokens', 0)
                        duration = int((time.time() - start_time) * 1000)
                        cost_usd_api = usage.get('cost')  # Точная цена из OpenRouter
                        
                        fire_and_forget_audit(
                            user_id=0,
                            agent_slug="news_writer",
                            model=self.model,
                            messages=messages,
                            response_content=content,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            duration_ms=duration,
                            cost_usd_api=cost_usd_api
                        )
                    except Exception as audit_err:
                        logger.error(f"Writer Audit Log Failed: {audit_err}")
                    
                    # Парсим JSON ответ
                    try:
                        json_obj = json.loads(content)
                        article = WriterResponse.model_validate(json_obj)
                        return article, citations, image_url
                    except (json.JSONDecodeError, ValidationError) as e:
                        logger.error(f"Writer JSON Parsing Error: {e}. Content: {content[:100]}...")
                        continue
                        
                except Exception as e:
                    logger.warning(f"Writer Attempt {attempt + 1}/{retries} failed: {e}")
                    if attempt == retries - 1:
                        logger.error("Writer max retries reached")
                        return None, [], None
                    await asyncio.sleep(2 ** attempt)
        return None, [], None

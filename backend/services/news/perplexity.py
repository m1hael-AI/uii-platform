import os
import yaml
import json
from loguru import logger
import asyncio
import time
import httpx
from services.audit_service import fire_and_forget_audit
from typing import List, Optional, Dict, Any
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
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        """Загружает промпты из YAML файла."""
        try:
            # Путь относительно этого файла: ../../resources/default_prompts.yaml
            current_dir = os.path.dirname(__file__)
            yaml_path = os.path.join(current_dir, '../../resources/default_prompts.yaml')
            
            # Нормализуем путь
            yaml_path = os.path.abspath(yaml_path)
            
            if not os.path.exists(yaml_path):
                logger.error(f"Prompts file not found at {yaml_path}")
                return {}

            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('news_agent', {})
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            return {}

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
                        
                        fire_and_forget_audit(
                            user_id=0, # System
                            agent_slug="news_agent",
                            model=self.model,
                            messages=messages,
                            response_content=content,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            duration_ms=duration
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

    async def search_news(self, query: str = None, exclude_titles: List[str] = None) -> List[NewsItemSchema]:
        """
        HARVESTER: Ищет новости.
        Если query задан - ищет по теме (User Search).
        Если query нет - ищет главные новости за сутки (Nightly Worker).
        """
        prompts = self.prompts.get('harvester', {})
        system_prompt = prompts.get('system_prompt', "You are a news aggregator.")
        
        user_content = f"Date: {asyncio.get_event_loop().time()}" # Hack: real time needed? Perplexity knows time.
        # Лучше просто дать инструкцию.
        
        if query:
            user_content = f"Topic: {query}. Find fresh news."
            if exclude_titles:
                user_content += f"\nEXCLUDE these known news: {', '.join(exclude_titles[:5])}..."
        else:
            user_content = "Find top AI news for the last 24 hours."

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

    async def generate_article(self, news_item: NewsItemSchema) -> Optional[WriterResponse]:
        """
        WRITER: Пишет статью по заголовку и ссылкам.
        """
        prompts = self.prompts.get('writer', {})
        system_prompt = prompts.get('system_prompt', "You are a tech journalist.")
        
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
        
        return await self._request(messages, WriterResponse)

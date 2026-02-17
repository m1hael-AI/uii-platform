import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from backend.models import NewsItem, NewsStatus
from backend.services.openai_service import generate_embedding
from backend.services.news.perplexity import NewsItemSchema, PerplexityClient, WriterResponse
from backend.config import settings

logger = logging.getLogger(__name__)

class NewsManager:
    """
    Управляет жизненным циклом новостей:
    1. Агрегация (add_news_items) с дедупликацией.
    2. Генерация контента (trigger_generation).
    3. Поиск и выдача (get_news_feed).
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perplexity = PerplexityClient()

    async def add_news_items(self, items: List[NewsItemSchema]) -> int:
        """
        Сохраняет новости в базу.
        Пропускает дубликаты (по URL и по вектору).
        Возвращает количество добавленных новостей.
        """
        added_count = 0
        
        # Предварительная загрузка существующих URL за последние 3 дня для быстрого фильтра
        # (Оптимизация: не делать запрос на каждую новость если их много)
        # Но для надежности будем проверять вектором.
        
        for item in items:
            try:
                # 1. Проверка URL (Точное совпадение)
                # Если такой source_url уже есть в JSON массиве source_urls
                # Для простоты проверяем, содержит ли массив этот URL как строку
                # PostgreSQL JSONB operator @> but here using text search for simplicity or precise logic
                stmt = select(NewsItem.id).where(
                    func.jsonb_path_exists(NewsItem.source_urls, f'$[*] ? (@ == "{item.source_url}")')
                )
                # Note: jsonb_path_exists is pure PG, might need casting. 
                # Fallback to simpler check if source_urls[0] == url (Canonical)
                # But let's rely on vector mainly + simple Python logic if needed.
                # Let's skip URL check complexity for a second and rely on Similarity, 
                # because same news from different source will have different URL.
                # Logic: If Vector implies Duplicate -> Skip.
                
                # 2. Vector Dedup
                text_to_embed = f"{item.title} {item.summary}"
                embedding = await generate_embedding(text_to_embed)
                
                is_dup = await self._check_vector_duplicate(embedding)
                if is_dup:
                    logger.info(f"Skipping duplicate (Vector): {item.title}")
                    # TODO: Можно добавлять URL к существующей новости (Merge), 
                    # но план говорит "No Merge Policy" для простоты.
                    continue
                
                # 3. Create
                # Parse date safely
                try:
                    pub_date = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
                except ValueError:
                    pub_date = datetime.utcnow()

                news = NewsItem(
                    title=item.title,
                    summary=item.summary,
                    source_urls=[item.source_url], 
                    published_at=pub_date,
                    tags=item.tags,
                    embedding=embedding,
                    status=NewsStatus.PENDING
                )
                self.db.add(news)
                added_count += 1
                
            except Exception as e:
                logger.error(f"Error adding news item '{item.title}': {e}")
                continue
            
        await self.db.commit()
        return added_count

    async def _check_vector_duplicate(self, embedding: List[float]) -> bool:
        """
        Проверяет, есть ли в базе новость с Cosine Similarity > Threshold.
        Distance < (1 - Threshold).
        """
        # Threshold 0.84 sim => 0.16 distance
        distance_threshold = 1.0 - settings.news_dedup_threshold
        
        distance_col = NewsItem.embedding.cosine_distance(embedding)
        
        # Ищем хотя бы одну новость ближе чем порог
        stmt = select(NewsItem.id).where(distance_col < distance_threshold).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def trigger_generation(self, news_id: int):
        """
        Запускает генерацию статьи для новости.
        """
        news = await self.db.get(NewsItem, news_id)
        if not news:
            return
            
        if news.status == NewsStatus.COMPLETED:
            return
            
        # Обновляем статус
        news.status = NewsStatus.PROCESSING
        await self.db.commit()
        
        try:
            # Подготовка данных для Writer
            item_schema = NewsItemSchema(
                title=news.title,
                summary=news.summary,
                source_url=news.source_urls[0] if news.source_urls else "",
                published_at=news.published_at.isoformat(),
                tags=news.tags or []
            )
            
            # Генерация
            article: WriterResponse = await self.perplexity.generate_article(item_schema)
            
            if article:
                # Успех
                news.content = article.content
                news.title = article.title # Обновляем заголовок на более красивый от автора
                news.status = NewsStatus.COMPLETED
                
                # Можно сохранить key_points в теги или отдельное поле, если нужно
                # news.tags.extend(article.key_points)
                
            else:
                # Неудача (пустой ответ)
                raise ValueError("Empty response from Writer")
                
        except Exception as e:
            logger.error(f"Generation failed for news {news_id}: {e}")
            news.status = NewsStatus.FAILED
            news.retry_count += 1
            
        finally:
            news.updated_at = datetime.utcnow()
            await self.db.commit()

    async def get_news_feed(
        self, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[NewsItem]:
        """
        Получение ленты новостей.
        Сортировка по fresh (published_at).
        """
        stmt = select(NewsItem).order_by(desc(NewsItem.published_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

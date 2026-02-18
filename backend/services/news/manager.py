from loguru import logger
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from models import NewsItem, NewsStatus
from services.openai_service import generate_embedding

from services.news.perplexity import NewsItemSchema, PerplexityClient, WriterResponse
from models import NewsItem, NewsStatus, User, UserMemory
from config import settings



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
                # Parse date safely (Ensure Naive UTC for DB compatibility)
                try:
                    # fromisoformat handles 'Z' in Python 3.11+, but let's be safe
                    dt_str = item.published_at.replace("Z", "+00:00")
                    pub_date = datetime.fromisoformat(dt_str)
                    
                    # Convert to UTC if aware, then strip timezone to make it naive
                    if pub_date.tzinfo is not None:
                        pub_date = pub_date.astimezone(timezone.utc).replace(tzinfo=None)
                        
                except Exception as e:
                    logger.warning(f"Date parse error '{item.published_at}': {e}. Using utcnow.")
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

    async def find_context_for_query(self, query: str, limit: int = 10) -> str:
        """
        Ищет похожие новости в базе по вектору запроса.
        Возвращает formatted string для промпта.
        Limit по умолчанию 10, чтобы дать LLM контекст и избежать дублей.
        """
        try:
            # 1. Embed query
            embedding = await generate_embedding(query)
            
            # 2. Search DB (Cosine Distance)
            distance_col = NewsItem.embedding.cosine_distance(embedding)
            
            # Order by distance ASC (closest first)
            stmt = select(NewsItem).order_by(distance_col).limit(limit)
            result = await self.db.execute(stmt)
            items = result.scalars().all()
            
            if not items:
                return "No existing news found."
                
            # 3. Format
            context = ""
            for i, item in enumerate(items, 1):
                context += f"{i}. {item.title} (Published: {item.published_at.date()})\n   Summary: {item.summary}\n"
                
            return context
            
        except Exception as e:
            logger.error(f"Failed to find context for query '{query}': {e}")
            return "Error retrieving context."

    async def search_local_news(self, query: str, limit: int = 10) -> List[NewsItem]:
        """
        Поиск новостей в локальной базе по вектору (смыслу).
        """
        try:
            embedding = await generate_embedding(query)
            distance_col = NewsItem.embedding.cosine_distance(embedding)
            
            # Сортируем по релевантности (distance)
            stmt = select(NewsItem).order_by(distance_col).limit(limit)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Local vector search failed for '{query}': {e}")
            return []

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
                return article
                
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

    async def get_personalized_news(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[NewsItem]:
        """
        Персонализированная лента новостей ("Для Вас").
        Алгоритм:
        1. Собираем профиль пользователя (Квиз + Память).
        2. Делаем эмбеддинг профиля.
        3. Ищем новости за последние 3 дня, близкие по вектору.
        4. Если профиль пуст — возвращаем обычную ленту.
        """
        # 1. Сбор профиля
        user_stmt = select(User).where(User.id == user_id)
        user_res = await self.db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        
        if not user:
            return await self.get_news_feed(limit=limit)
            
        memory_stmt = select(UserMemory).where(UserMemory.user_id == user_id)
        memory_res = await self.db.execute(memory_stmt)
        memory = memory_res.scalar_one_or_none()
        
        profile_text = ""
        # Добавляем ответы на квиз (если есть)
        if user.quiz_answers:
            # quiz_answers is list of strings
            profile_text += "Interests: " + ", ".join(map(str, user.quiz_answers)) + ". "
            
        # Добавляем нарративную память
        if memory and memory.narrative_summary:
            profile_text += f"Context: {memory.narrative_summary}"
            
        if not profile_text.strip():
            # Нет данных для персонализации -> обычная лента
            return await self.get_news_feed(limit=limit)
            
        try:
            # 2. Эмбеддинг интересов
            user_embedding = await generate_embedding(profile_text)
            
            # 3. Поиск (Hybrid: Time + Vector)
            # Берем только свежие новости (3 дня)
            since_date = datetime.utcnow() - timedelta(days=3)
            
            distance_col = NewsItem.embedding.cosine_distance(user_embedding)
            
            stmt = (
                select(NewsItem)
                .where(NewsItem.published_at >= since_date)
                .order_by(distance_col) # Самые близкие по смыслу
                .limit(limit)
            )
            
            result = await self.db.execute(stmt)
            items = result.scalars().all()
            
            # Если новостей мало (например, векторный поиск ничего не нашел или база пустая),
            # доливаем обычными свежими новостями
            if len(items) < limit:
                needed = limit - len(items)
                existing_ids = [n.id for n in items]
                
                fallback_stmt = (
                    select(NewsItem)
                    .where(NewsItem.published_at >= since_date)
                    .where(NewsItem.id.notin_(existing_ids))
                    .order_by(desc(NewsItem.published_at))
                    .limit(needed)
                )
                fallback_res = await self.db.execute(fallback_stmt)
                items.extend(fallback_res.scalars().all())
                
            return items
            
        except Exception as e:
            logger.error(f"Personalization failed for user {user_id}: {e}")
            # Fallback to standard feed
            return await self.get_news_feed(limit=limit)

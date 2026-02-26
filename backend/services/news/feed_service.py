import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from loguru import logger
from openai import AsyncOpenAI
import pytz

from models import UserMemory, NewsItem, UserNewsFeedCache, UserViewedNews, NewsStatus, NewsSettings
from config import settings

class FeedService:
    """
    Сервис для формирования персональной ленты новостей "Для вас".
    Использует векторный поиск (pgvector) + LLM Re-ranking.
    Кэширует результаты до 05:00 утра текущего/следующего дня.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
    def _is_cache_valid(self, generated_at: datetime) -> bool:
        """
        Проверяет, валиден ли кэш.
        Кэш валиден, если он был сгенерирован ПОСЛЕ 05:00 утра текущего календарного дня
        по UTC (или серверному времени).
        """
        now = datetime.utcnow()
        # Определяем границу "сегодня в 05:00"
        reset_time_today = now.replace(hour=5, minute=0, second=0, microsecond=0)
        
        if now < reset_time_today:
            # Если сейчас 03:00 ночи, граница сброса была ВЧЕРА в 05:00
            reset_boundary = reset_time_today - timedelta(days=1)
        else:
            # Если сейчас 10:00 утра, граница сброса была СЕГОДНЯ в 05:00
            reset_boundary = reset_time_today
            
        return generated_at >= reset_boundary

    async def get_for_you_feed(self, user_id: int) -> List[NewsItem]:
        """
        Главный метод: Возвращает персональную ленту новостей.
        Пайплайн: Cache -> Vector Filter (20, <7 days, not viewed) -> LLM Rerank -> Cache -> Return.
        """
        logger.info(f"📰 Запрос ленты 'Для вас' для пользователя {user_id}")
        
        # 1. Проверяем кэш
        result = await self.db.execute(
            select(UserNewsFeedCache).where(UserNewsFeedCache.user_id == user_id)
        )
        cache = result.scalar_one_or_none()
        
        if cache and self._is_cache_valid(cache.generated_at):
            logger.info(f"🎯 Возвращаем кэшированную ленту 'Для вас' (сгенерировано {cache.generated_at})")
            return await self._get_news_by_ids(cache.news_ids)
            
        logger.info(f"🔄 Кэш устарел или отсутствует. Запускаем LLM Re-ranking pipeline...")
        
        # 2. Получаем настройки AI News (для параметров For You)
        settings_result = await self.db.execute(select(NewsSettings).limit(1))
        news_settings = settings_result.scalar_one_or_none()
        
        if not news_settings or not news_settings.foryou_enabled:
            logger.info("ℹ️ Лента 'Для вас' отключена в настройках админки.")
            return []
            
        vector_limit = news_settings.foryou_vector_limit
        days_limit = news_settings.foryou_days_limit
        rerank_prompt = news_settings.foryou_rerank_prompt
        
        # 3. Получаем профиль пользователя
        mem_result = await self.db.execute(
            select(UserMemory).where(UserMemory.user_id == user_id)
        )
        memory = mem_result.scalar_one_or_none()
        
        if not memory or not memory.narrative_summary:
            logger.warning(f"⚠️ У пользователя {user_id} нет профиля (UserMemory). Возвращаем пустую ленту.")
            return []
            
        profile_text = memory.narrative_summary
        
        # 4. Векторный Поиск (Грубый фильтр)
        top_news = await self._vector_search_top(user_id, profile_text, vector_limit, days_limit)
        
        if not top_news:
             logger.info("ℹ️ Не найдено ни одной подходящей свежей новости.")
             return []
             
        # 5. LLM Re-ranking (Тонкий фильтр)
        best_news_ids = await self._llm_rerank(profile_text, top_news, rerank_prompt, days_limit)
        
        if not best_news_ids:
            logger.warning("⚠️ LLM не выбрала ни одной новости. Сохраняем пустой кэш.")
            best_news_ids = []
            
        # 5. Сохраняем в кэш
        if cache:
            cache.news_ids = best_news_ids
            cache.generated_at = datetime.utcnow()
        else:
            cache = UserNewsFeedCache(
                user_id=user_id,
                news_ids=best_news_ids,
                generated_at=datetime.utcnow()
            )
            self.db.add(cache)
            
        await self.db.commit()
        
        # 7. Возвращаем результат
        return await self._get_news_by_ids(best_news_ids)

    async def _vector_search_top(self, user_id: int, profile_text: str, vector_limit: int, days_limit: int) -> List[NewsItem]:
        """
        Ищет заданное количество самых релевантных непрочитанных новостей за последние N дней.
        """
        # Генерируем вектор для биографии
        from services.openai_service import generate_embedding
        profile_embedding = await generate_embedding(profile_text)
        
        if not profile_embedding:
            return []

        cutoff_date = datetime.utcnow() - timedelta(days=days_limit)
        
        # Получаем список ID прочитанных новостей
        viewed_result = await self.db.execute(
            select(UserViewedNews.news_id).where(UserViewedNews.user_id == user_id)
        )
        viewed_ids = [row[0] for row in viewed_result.all()]
        
        # Строим гибридный запрос
        query = (
            select(NewsItem)
            .where(
                and_(
                    NewsItem.status == NewsStatus.COMPLETED,
                    NewsItem.published_at >= cutoff_date
                )
            )
        )
        
        if viewed_ids:
            query = query.where(NewsItem.id.not_in(viewed_ids))
            
        # Сортируем по векторной близости (косинусное расстояние: 1 - cosine_similarity)
        # Обрати внимание: pgvector <-> operator это L2 расстояние, 
        # <=> это косинусное расстояние. Для эмбеддингов OpenAI используем <=>.
        query = query.order_by(NewsItem.embedding.cosine_distance(profile_embedding)).limit(vector_limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def _llm_rerank(self, profile_text: str, news_list: List[NewsItem], prompt_template: str, days_limit: int) -> List[int]:
        """
        Скармливает LLM профиль и новости, просит выбрать только самые релевантные на основе промпта из настроек.
        """
        # Формируем список новостей для LLM
        news_json_list = []
        for n in news_list:
            news_json_list.append({
                "id": n.id,
                "title": n.title,
                "summary": n.summary,
            })
            
        news_json_str = json.dumps(news_json_list, ensure_ascii=False, indent=2)
        
        try:
            prompt = prompt_template.format(
                profile_text=profile_text,
                news_json_list=news_json_str,
                days_limit=days_limit
            )
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования промпта For You: {e}. Используем сырой промпт.")
            prompt = prompt_template

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            selected_ids = data.get("selected_ids", [])
            # Убеждаемся, что ID действительно из тех, что мы передали
            valid_ids = [n.id for n in news_list]
            final_ids = [i for i in selected_ids if i in valid_ids]
            
            logger.info(f"🧠 LLM выбрала {len(final_ids)} новостей из {len(news_list)} предложенных.")
            return final_ids
            
        except Exception as e:
            logger.error(f"❌ Ошибка при LLM Re-ranking: {e}")
            return []

    async def _get_news_by_ids(self, news_ids: List[int]) -> List[NewsItem]:
        """
        Возвращает новости из базы, сохраняя порядок ID.
        """
        if not news_ids:
            return []
            
        result = await self.db.execute(
            select(NewsItem).where(NewsItem.id.in_(news_ids))
        )
        news_dict = {item.id: item for item in result.scalars().all()}
        
        # Возвращаем в том же порядке, в котором шли ID (как отсортировала LLM)
        ordered_news = [news_dict[nid] for nid in news_ids if nid in news_dict]
        return ordered_news

    async def mark_news_as_viewed(self, user_id: int, news_id: int):
        """
        Отмечает новость как прочитанную пользователем.
        """
        # Проверяем не читал ли он ее уже
        result = await self.db.execute(
            select(UserViewedNews).where(
                and_(UserViewedNews.user_id == user_id, UserViewedNews.news_id == news_id)
            )
        )
        if result.scalar_one_or_none():
            return # Уже прочитано
            
        view_record = UserViewedNews(user_id=user_id, news_id=news_id)
        self.db.add(view_record)
        await self.db.commit()

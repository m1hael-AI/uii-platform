from fastapi import HTTPException, status, Request
from utils.redis_client import get_redis
from config import settings

# Настройки лимитов по умолчанию
DEFAULT_RATE_LIMIT = 15  # запросов
DEFAULT_TIME_WINDOW = 60 # секунд

class RateLimiter:
    def __init__(self, limit: int = DEFAULT_RATE_LIMIT, window: int = DEFAULT_TIME_WINDOW):
        self.limit = limit
        self.window = window

    async def __call__(self, request: Request):
        # Если это не авторизованный запрос (нет user_id в state), пропускаем или используем IP
        user = getattr(request.state, "user", None)
        
        # Determine strict key
        if user:
            key = f"rate_limit:user:{user.id}"
        else:
            client_ip = request.client.host
            key = f"rate_limit:ip:{client_ip}"

        redis = await get_redis()
        if not redis:
            return

        # 1. Get Dynamic Limit from Settings
        # We need a DB session. We can try to get it from request state if available, or create new.
        # But for performance (dependency), creating session every time might be heavy?
        # A Better way is to cache the limit in Redis or memory.
        # Let's use Redis caching for the LIMIT value itself "system:rate_limit" for 1 minute.
        
        current_limit = self.limit # Default fallback
        
        # Try to get cached global limit
        cached_limit = await redis.get("system:global_rate_limit")
        if cached_limit:
            current_limit = int(cached_limit)
        else:
            # Fetch from DB: We need to import here to avoid circular
            from database import async_session_factory
            from sqlalchemy import select
            from models import ProactivitySettings
            
            async with async_session_factory() as db:
                 res = await db.execute(select(ProactivitySettings))
                 settings_obj = res.scalar_one_or_none()
                 if settings_obj and settings_obj.rate_limit_per_minute > 0:
                     current_limit = settings_obj.rate_limit_per_minute
            
            # Cache it for 60 seconds
            await redis.setex("system:global_rate_limit", 60, current_limit)

        # 2. Increment & Check
        current_count = await redis.incr(key)
        
        # If first request, set window expiry
        if current_count == 1:
            await redis.expire(key, self.window)
            
        if current_count > current_limit:
             raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({current_limit}/min). Try again later."
            )

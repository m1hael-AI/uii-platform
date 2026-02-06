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
        # Но мы используем это ПОСЛЕ авторизации
        user = getattr(request.state, "user", None)
        
        # Если юзера нет в state (например, dependency rate limit стоит ДО аутентификации),
        # то попробуем достать из заголовка Authorization (Decode JWT) 
        # но лучше полагаться на auth dependency.
        
        # В нашем случае мы будем использовать user_id если он есть, иначе IP
        if user:
            key = f"rate_limit:user:{user.id}"
        else:
            client_ip = request.client.host
            key = f"rate_limit:ip:{client_ip}"

        redis = await get_redis()
        if not redis:
            # Если Redis не подключен (dev mode без redis?), пропускаем
            return

        # Инкремент
        current_count = await redis.incr(key)
        
        # Если это первый запрос - ставим TTL
        if current_count == 1:
            await redis.expire(key, self.window)
            
        if current_count > self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {self.window} seconds."
            )

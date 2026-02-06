from redis import asyncio as aioredis
from config import settings

class RedisClient:
    def __init__(self):
        self.redis = None

    async def connect(self):
        if settings.redis_url:
            self.redis = aioredis.from_url(
                settings.redis_url, 
                encoding="utf-8", 
                decode_responses=True
            )
            print("✅ Redis connected (FastAPI)")

    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            print("❌ Redis disconnected")

    async def get_client(self):
        if not self.redis:
            await self.connect()
        return self.redis

redis_client = RedisClient()

async def get_redis():
    return await redis_client.get_client()

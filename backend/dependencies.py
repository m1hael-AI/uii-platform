from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_factory
from models import User
from services.auth import decode_access_token
from config import settings
from utils.redis_client import get_redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_db():
    async with async_session_factory() as session:
        yield session

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
        
    # Find user by Primary Key (id)
    # Token 'sub' now contains database ID, not telegram ID
    stmt = select(User).where(User.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    return user

async def rate_limiter(user: User = Depends(get_current_user)):
    """
    Лимит: 15 сообщений в минуту на пользователя.
    """
    limit = 15
    window = 60
    
    redis = await get_redis()
    if not redis:
        return # Skip if Redis unavailable
        
    key = f"rate_limit:chat:{user.id}"
    
    try:
        current_count = await redis.incr(key)
        if current_count == 1:
            await redis.expire(key, window)
            
        if current_count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов. Пожалуйста, подождите минуту."
            )
    except Exception as e:
        # Fallback if Redis fails
        print(f"Rate limiter error: {e}")

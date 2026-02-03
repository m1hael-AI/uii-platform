from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создает JWT токен доступа.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Декодирует и проверяет JWT токен.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

# --- Magic Link Logic ---
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from models import MagicLinkToken

async def create_magic_link(db: AsyncSession, user_id: int) -> str:
    """
    Генерирует одноразовый токен. Отзывает все старые активные токены юзера.
    """
    # 1. Revoke old active tokens
    statement = select(MagicLinkToken).where(
        MagicLinkToken.user_id == user_id,
        MagicLinkToken.is_revoked == False,
        MagicLinkToken.is_used == False,
        MagicLinkToken.expires_at > datetime.utcnow()
    )
    results = await db.execute(statement)
    old_tokens = results.scalars().all()
    for t in old_tokens:
        t.is_revoked = True
        db.add(t)
    
    # 2. Create new
    token_str = secrets.token_urlsafe(32) 
    expires = datetime.utcnow() + timedelta(minutes=10)
    
    new_token = MagicLinkToken(
        user_id=user_id,
        token=token_str,
        expires_at=expires
    )
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)
    
    return token_str

async def verify_magic_link(db: AsyncSession, token_str: str) -> Optional[int]:
    """
    Проверяет токен. Если валиден - помечает used и возвращает user_id.
    """
    stmt = select(MagicLinkToken).where(MagicLinkToken.token == token_str)
    res = await db.execute(stmt)
    token_obj = res.scalar_one_or_none()
    
    if not token_obj:
        return None # Not found
        
    # Check validity
    if token_obj.is_revoked:
        return None # Revoked
    if token_obj.is_used:
        return None # Already used
    if token_obj.expires_at < datetime.utcnow():
        return None # Expired
        
    # Mark used
    token_obj.is_used = True
    db.add(token_obj)
    await db.commit()
    
    return token_obj.user_id

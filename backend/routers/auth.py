from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from hashlib import sha256
import hmac
import time

from models import User, UserRole
from dependencies import get_db
from services.auth import create_access_token, verify_password, get_password_hash, verify_magic_link
from config import settings
from loguru import logger

router = APIRouter(prefix="/auth", tags=["auth"])

# === MODELS ===

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str


@router.get("/magic", response_model=Token)
async def magic_link_login(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Вход по одноразовой ссылке.
    """
    user_id = await verify_magic_link(db, token)
    if not user_id:
        logger.warning(f"⚠️ Magic Link verification failed: token={token[:10]}...")
        raise HTTPException(
            status_code=400, 
            detail="Ссылка недействительна или устарела. Запросите новую в боте."
        )
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(days=7)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
         raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        tg_first_name=user_in.first_name,
        tg_last_name=user_in.last_name,
        role=UserRole.USER,
        is_onboarded=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create token
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(days=7)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    # Form data has 'username' and 'password'
    # We treat 'username' as email
    email = form_data.username
    password = form_data.password
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.hashed_password:
        raise HTTPException(status_code=400, detail="This account uses Telegram login. Please set a password.")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(hours=settings.jwt_expire_hours)
    )
    return {"access_token": access_token, "token_type": "bearer"}



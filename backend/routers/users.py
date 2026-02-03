from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dependencies import get_current_user, get_db
from models import User, UserAction

router = APIRouter(prefix="/users", tags=["users"])

# --- Schemas ---
class UserResponse(BaseModel):
    id: int
    tg_id: Optional[int] = None
    tg_username: Optional[str] = None
    is_onboarded: bool = False
    tg_first_name: Optional[str] = None
    tg_last_name: Optional[str] = None
    tg_photo_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"
    has_password: bool = False

    class Config:
        from_attributes = True

class PasswordUpdate(BaseModel):
    new_password: str
    old_password: Optional[str] = None

# Use absolute import for services if needed, or relative
from services.auth import get_password_hash, verify_password
from fastapi import HTTPException

class OnboardingUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    quiz_answers: Optional[List[str]] = None
    
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    resp = UserResponse.model_validate(current_user)
    resp.has_password = bool(current_user.hashed_password)
    return resp

@router.patch("/me")
async def update_user_me(
    update_data: OnboardingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if update_data.phone is not None:
        current_user.phone = update_data.phone
    if update_data.email is not None:
        current_user.email = update_data.email
    if update_data.quiz_answers is not None:
        current_user.quiz_answers = update_data.quiz_answers
    
    if update_data.quiz_answers and len(update_data.quiz_answers) > 0:
        current_user.is_onboarded = True
        log = UserAction(user_id=current_user.id, action="onboarding_complete_web", payload={"email": current_user.email})
        db.add(log)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return {"status": "ok", "is_onboarded": current_user.is_onboarded}

@router.post("/me/password")
async def set_password(
    pwd_data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set or change user password"""
    
    # 1. Validation for length
    if len(pwd_data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Пароль слишком короткий (минимум 8 символов)")
    if len(pwd_data.new_password) > 128:
        raise HTTPException(status_code=400, detail="Пароль слишком длинный (максимум 128 символов)")

    # Security check: if user already has a password, they MUST provide old_password
    if current_user.hashed_password:
        if not pwd_data.old_password:
             raise HTTPException(status_code=400, detail="Старый пароль обязателен для смены пароля")
        
        if not verify_password(pwd_data.old_password, current_user.hashed_password):
             raise HTTPException(status_code=400, detail="Неверный старый пароль")

    hashed = get_password_hash(pwd_data.new_password)
    current_user.hashed_password = hashed
    
    db.add(current_user)
    await db.commit()
    
    return {"status": "ok", "message": "Password updated"}


# --- Avatar Endpoints ---

from fastapi import UploadFile, File
from services.user_service import sync_user_avatar_from_telegram, upload_manual_avatar

@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manual upload of user avatar"""
    url = await upload_manual_avatar(current_user, file, db)
    return {"status": "ok", "avatar_url": url}

@router.post("/me/avatar/sync")
async def sync_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Force sync avatar from Telegram"""
    url = await sync_user_avatar_from_telegram(current_user, db)
    if not url:
        raise HTTPException(status_code=404, detail="Не удалось получить фото из Telegram (или у пользователя нет tg_id)")
    
    return {"status": "ok", "avatar_url": url}


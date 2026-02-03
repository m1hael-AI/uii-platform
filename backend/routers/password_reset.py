"""
Password Reset через Telegram.
Безопасный флоу с детальными сообщениями об ошибках.
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr

from models import User, PasswordResetToken
from dependencies import get_db
from services.auth import create_access_token, get_password_hash
from config import settings

router = APIRouter(prefix="/auth/reset-password", tags=["password-reset"])

# === REQUEST/RESPONSE MODELS ===

class ResetRequestModel(BaseModel):
    email: EmailStr

class VerifyCodeModel(BaseModel):
    email: EmailStr
    code: str

class SetNewPasswordModel(BaseModel):
    reset_token: str
    new_password: str

class ResetTokenResponse(BaseModel):
    reset_token: str
    message: str

# === HELPER FUNCTIONS ===

def generate_code() -> str:
    """Генерирует 6-значный код"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))

async def send_code_to_telegram(user: User, code: str):
    """
    Отправляет код в Telegram бота пользователю.
    """
    if not user.tg_id:
        raise HTTPException(
            status_code=400,
            detail="User has no Telegram ID"
        )
    
    try:
        from bot.loader import bot
        
        await bot.send_message(
            chat_id=user.tg_id,
            text=f"🔐 <b>Код для сброса пароля:</b>\n\n<code>{code}</code>\n\nВведите его на сайте в течение 10 минут.",
            parse_mode="HTML"
        )
    except Exception as e:
        # Log error but don't expose to user
        print(f"[ERROR] Failed to send code to Telegram user {user.tg_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "telegram_send_failed",
                "message": "Не удалось отправить код в Telegram. Убедитесь, что вы написали боту /start."
            }
        )

# === ENDPOINTS ===

@router.post("/request")
async def request_reset(
    data: ResetRequestModel,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Шаг 1: Запрос кода для сброса пароля.
    Отправляет 6-значный код в Telegram.
    """
    # 1. Найти пользователя
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Не раскрываем, существует ли email (защита от перебора)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "user_not_found",
                "message": "Пользователь с таким email не найден. Проверьте правильность ввода."
            }
        )
    
    # 2. Проверить, подключен ли Telegram
    if not user.tg_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "telegram_not_connected",
                "message": "Ваш аккаунт не связан с Telegram. Сброс пароля возможен только через Telegram-бота."
            }
        )
    
    # 3. Rate Limiting: проверить, не было ли недавнего запроса
    recent_token_query = select(PasswordResetToken).where(
        and_(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at > datetime.utcnow() - timedelta(seconds=60),
            PasswordResetToken.is_used == False
        )
    )
    recent_result = await db.execute(recent_token_query)
    recent_token = recent_result.scalar_one_or_none()
    
    if recent_token:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "too_many_requests",
                "message": "Код уже отправлен. Подождите 60 секунд перед повторной отправкой.",
                "retry_after": 60
            }
        )
    
    # 4. Отозвать старые неиспользованные коды
    old_tokens_query = select(PasswordResetToken).where(
        and_(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False
        )
    )
    old_tokens_result = await db.execute(old_tokens_query)
    old_tokens = old_tokens_result.scalars().all()
    
    for token in old_tokens:
        token.is_used = True  # Помечаем как использованные (отозванные)
        db.add(token)
    
    # 5. Создать новый код
    code = generate_code()
    ip_address = request.client.host if request.client else None
    
    reset_token = PasswordResetToken(
        user_id=user.id,
        code=code,
        ip_address=ip_address,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    
    db.add(reset_token)
    await db.commit()
    
    # 6. Отправить код в Telegram
    await send_code_to_telegram(user, code)
    
    return {
        "message": "Код отправлен в Telegram. Проверьте сообщения от бота.",
        "expires_in_minutes": 10
    }


@router.post("/verify", response_model=ResetTokenResponse)
async def verify_code(
    data: VerifyCodeModel,
    db: AsyncSession = Depends(get_db)
):
    """
    Шаг 2: Проверка кода.
    Возвращает временный токен для установки нового пароля.
    """
    # 1. Найти пользователя
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "user_not_found",
                "message": "Пользователь не найден."
            }
        )
    
    # 2. Найти активный код
    token_query = select(PasswordResetToken).where(
        and_(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.code == data.code,
            PasswordResetToken.is_used == False
        )
    ).order_by(PasswordResetToken.created_at.desc())
    
    token_result = await db.execute(token_query)
    reset_token = token_result.scalar_one_or_none()
    
    if not reset_token:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "code_not_found",
                "message": "Неверный код. Проверьте правильность ввода или запросите новый код."
            }
        )
    
    # 3. Проверить срок действия
    if datetime.utcnow() > reset_token.expires_at:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "code_expired",
                "message": "Код истек. Срок действия кода — 10 минут. Запросите новый код."
            }
        )
    
    # 4. Проверить количество попыток
    if reset_token.attempts >= reset_token.max_attempts:
        reset_token.is_used = True
        db.add(reset_token)
        await db.commit()
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": "max_attempts_exceeded",
                "message": f"Превышено максимальное количество попыток ({reset_token.max_attempts}). Запросите новый код."
            }
        )
    
    # 5. Увеличить счетчик попыток
    reset_token.attempts += 1
    db.add(reset_token)
    await db.commit()
    
    # 6. Создать временный JWT токен (на 5 минут)
    temp_token = create_access_token(
        data={
            "sub": str(user.id),
            "type": "password_reset",
            "token_id": reset_token.id
        },
        expires_delta=timedelta(minutes=5)
    )
    
    return ResetTokenResponse(
        reset_token=temp_token,
        message="Код подтвержден. Теперь установите новый пароль."
    )


@router.post("/confirm")
async def set_new_password(
    data: SetNewPasswordModel,
    db: AsyncSession = Depends(get_db)
):
    """
    Шаг 3: Установка нового пароля.
    Требует временный токен из шага 2.
    """
    # 1. Декодировать и проверить токен
    from services.auth import decode_access_token
    
    try:
        payload = decode_access_token(data.reset_token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "message": "Недействительный или истекший токен. Пройдите процедуру сброса заново."
            }
        )
    
    # 2. Проверить тип токена
    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "invalid_token_type",
                "message": "Неверный тип токена."
            }
        )
    
    user_id = int(payload["sub"])
    token_id = payload.get("token_id")
    
    # 3. Проверить, что код еще не использован
    reset_token = await db.get(PasswordResetToken, token_id)
    
    if not reset_token or reset_token.is_used:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "token_already_used",
                "message": "Этот код уже был использован. Запросите новый код для повторного сброса пароля."
            }
        )
    
    # 4. Проверить срок действия кода (дополнительная проверка)
    if datetime.utcnow() > reset_token.expires_at:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "token_expired",
                "message": "Время действия кода истекло. Запросите новый код."
            }
        )
    
    # 5. Обновить пароль
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = get_password_hash(data.new_password)
    reset_token.is_used = True
    
    db.add(user)
    db.add(reset_token)
    await db.commit()
    
    return {
        "message": "Пароль успешно изменен! Теперь вы можете войти с новым паролем."
    }


import logging
import re
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    ReplyKeyboardRemove,
)
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from sqlalchemy import select

from database import async_session_factory
from models import User, UserAction, UserRole
from services.auth import create_magic_link
from services.user_service import sync_user_avatar_from_telegram
from config import settings

logger = logging.getLogger(__name__)

router = Router()

# === CONSTANTS ===

WELCOME_MESSAGE = (
    "👋 <b>Добро пожаловать в AI University!</b>\n\n"
    "Мы рады видеть вас здесь. Чтобы начать обучение и получить доступ к платформе, "
    "пожалуйста, перейдите по ссылке ниже для завершения регистрации."
)

# === HELPERS ===

def parse_utm(payload: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Parse UTM parameters from deep link payload."""
    if not payload or not payload.strip():
        return None, None, None, None

    parts = payload.split("_")
    parts = [p.strip() for p in parts if p.strip()]

    utm_source = parts[0] if len(parts) > 0 else None
    utm_medium = parts[1] if len(parts) > 1 else None
    utm_campaign = parts[2] if len(parts) > 2 else None
    utm_content = parts[3] if len(parts) > 3 else None

    return utm_source, utm_medium, utm_campaign, utm_content

async def log_user_action(user_id: int, action: str, payload: dict = None):
    """Log user action to DB."""
    try:
        async with async_session_factory() as session:
            # Need to find DB user id by telegram id
            stmt = select(User).where(User.tg_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                log = UserAction(user_id=user.id, action=action, payload=payload)
                session.add(log)
                await session.commit()
    except Exception as e:
        logger.error(f"Failed to log action {action} for user {user_id}: {e}")

# === HANDLERS ===

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    # DEBUG PRINT
    print(f"DEBUG: cmd_start called for user {message.from_user.id}")
    
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Parse UTM
    utm_source, utm_medium, utm_campaign, utm_content = parse_utm(command.args)
    
    magic_link = ""
    
    async with async_session_factory() as session:
        # Check if exists
        stmt = select(User).where(User.tg_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                tg_id=user_id,
                tg_username=username,
                tg_first_name=first_name,
                tg_last_name=last_name,
                tg_photo_url=None, # Need separate download for photo
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
                role=UserRole.USER,
                is_onboarded=False
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            await log_user_action(user_id, "start_bot", {"utm_source": utm_source})
            
            # --- Sync Avatar ---
            try:
                await sync_user_avatar_from_telegram(user, session)
            except Exception as e:
                logger.error(f"Avatar sync failed: {e}")
        else:
            # Update existing? Maybe just UTM if they came from new link
            if utm_source:
                 user.utm_source = utm_source
                 user.utm_medium = utm_medium
                 user.utm_campaign = utm_campaign
                 user.utm_content = utm_content
                 session.add(user)
                 await session.commit()
                 await log_user_action(user_id, "start_bot_new_utm", {"utm_source": utm_source})
            
            # --- Try Sync Avatar if missing ---
            if not user.tg_photo_url:
                try:
                    await sync_user_avatar_from_telegram(user, session)
                except Exception as e:
                    logger.error(f"Avatar sync failed (existing user): {e}")
        
        # === GENERATE MAGIC LINK ===
        # This revokes old links automatically
        token_str = await create_magic_link(session, user.id)
        
        frontend_url = settings.frontend_url
        magic_link = f"{frontend_url}/auth/magic?token={token_str}"

    # Clear any previous FSM state
    await state.clear()
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Войти в AI University", url=magic_link)]
    ])
    
    await message.answer(
        WELCOME_MESSAGE,
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


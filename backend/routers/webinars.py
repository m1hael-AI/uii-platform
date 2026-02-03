from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from models import User, UserRole, Webinar, UserAction, WebinarSignup
from dependencies import get_current_user, get_db

router = APIRouter(prefix="/webinars", tags=["webinars"])

# === DTOs (Data Transfer Objects) ===

class WebinarBase(BaseModel):
    title: str
    description: Optional[str] = None
    video_url: Optional[str] = None
    connection_link: Optional[str] = None
    thumbnail_url: Optional[str] = None
    transcript_context: Optional[str] = ""
    is_upcoming: bool = False
    is_published: bool = True
    scheduled_at: Optional[datetime] = None
    speaker_name: Optional[str] = None
    duration_minutes: int = 60

class WebinarCreate(WebinarBase):
    pass

class WebinarUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    video_url: Optional[str] = None
    connection_link: Optional[str] = None
    thumbnail_url: Optional[str] = None
    transcript_context: Optional[str] = None
    is_upcoming: Optional[bool] = None
    is_published: Optional[bool] = None
    scheduled_at: Optional[datetime] = None
    speaker_name: Optional[str] = None
    duration_minutes: Optional[int] = None

class WebinarResponse(WebinarBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# === Endpoints ===

@router.get("", response_model=List[WebinarResponse])
async def list_webinars(
    filter_type: str = Query("all", enum=["all", "library", "upcoming"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список вебинаров.
    filter_type:
      - 'library': только прошедшие (is_upcoming=False, is_published=True)
      - 'upcoming': только будущие (is_upcoming=True, is_published=True)
      - 'all': все опубликованные
      - Админ видит всё.
    """
    query = select(Webinar).order_by(desc(Webinar.created_at))

    # Если не админ, показываем только опубликованные
    if current_user.role != UserRole.ADMIN:
        query = query.where(Webinar.is_published == True)

    if filter_type == "library":
        query = query.where(Webinar.is_upcoming == False)
    elif filter_type == "upcoming":
        query = query.where(Webinar.is_upcoming == True)

    
    result = await db.execute(query)
    webinars = result.scalars().all()
    return webinars

@router.get("/{webinar_id}", response_model=WebinarResponse)
async def get_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить один вебинар по ID"""
    query = select(Webinar).where(Webinar.id == webinar_id)
    if current_user.role != UserRole.ADMIN:
        query = query.where(Webinar.is_published == True)
        
    result = await db.execute(query)
    webinar = result.scalar_one_or_none()
    
    if not webinar:
        raise HTTPException(status_code=404, detail="Webinar not found")
        
    return webinar

@router.post("", response_model=WebinarResponse)
async def create_webinar(
    webinar_data: WebinarCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Создать новый вебинар"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_webinar = Webinar.model_validate(webinar_data)
    
    # Если это архивный вебинар, ставим дату создания сейчас (или можно передавать)
    if not new_webinar.scheduled_at:
        new_webinar.scheduled_at = datetime.utcnow()

    db.add(new_webinar)
    await db.commit()
    await db.refresh(new_webinar)
    return new_webinar

@router.patch("/{webinar_id}", response_model=WebinarResponse)
async def update_webinar(
    webinar_id: int,
    update_data: WebinarUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Обновить вебинар"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    webinar = await db.get(Webinar, webinar_id)
    if not webinar:
        raise HTTPException(status_code=404, detail="Webinar not found")
        
    # Partial update
    data = update_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(webinar, key, value)
        
    webinar.updated_at = datetime.utcnow()
    
    db.add(webinar)
    await db.commit()
    await db.refresh(webinar)
    return webinar

@router.delete("/{webinar_id}")
async def delete_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Удалить вебинар"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    webinar = await db.get(Webinar, webinar_id)
    if not webinar:
        raise HTTPException(status_code=404, detail="Webinar not found")
        
    await db.delete(webinar)
    await db.commit()
    return {"status": "deleted", "id": webinar_id}


# === Signup Endpoints (Dual Write: UserAction + WebinarSignup) ===

@router.post("/{webinar_id}/signup")
async def signup_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Записаться на вебинар (Dual Write: History + Notification Queue)"""
    # 1. Check if webinar exists
    webinar = await db.get(Webinar, webinar_id)
    if not webinar:
        raise HTTPException(status_code=404, detail="Webinar not found")

    # 2. Check if already signed up (Optimized check via WebinarSignup)
    query_signup = select(WebinarSignup).where(
        WebinarSignup.user_id == current_user.id,
        WebinarSignup.webinar_id == webinar_id
    )
    result_signup = await db.execute(query_signup)
    existing_signup = result_signup.scalar_one_or_none()
    
    if existing_signup:
         return {"status": "already_signed_up"}

    # 3. Create Notification Entry (WebinarSignup)
    new_signup = WebinarSignup(
        user_id=current_user.id,
        webinar_id=webinar_id
    )
    db.add(new_signup)
    
    # 4. Create Audit Log (UserAction) - for history
    new_action = UserAction(
        user_id=current_user.id,
        action="webinar_signup",
        payload={"webinar_id": webinar_id}
    )
    db.add(new_action)
    
    await db.commit()
    return {"status": "signed_up", "webinar_id": webinar_id}

@router.delete("/{webinar_id}/signup")
async def cancel_signup_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отменить запись (Dual Deletion)"""
    # 1. Delete from Notification Queue
    query_signup = select(WebinarSignup).where(
        WebinarSignup.user_id == current_user.id,
        WebinarSignup.webinar_id == webinar_id
    )
    result_signup = await db.execute(query_signup)
    signup = result_signup.scalar_one_or_none()
    
    if signup:
        await db.delete(signup)

    # 2. Add 'webinar_unsignup' event to Audit Log (Preserve History)
    unsignup_action = UserAction(
        user_id=current_user.id,
        action="webinar_unsignup",
        payload={"webinar_id": webinar_id}
    )
    db.add(unsignup_action)
            
    await db.commit()
    
    return {"status": "cancelled"}

@router.get("/{webinar_id}/signup")
async def check_signup_status(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Проверить, записан ли пользователь (fast check)"""
    query = select(WebinarSignup).where(
        WebinarSignup.user_id == current_user.id,
        WebinarSignup.webinar_id == webinar_id
    )
    result = await db.execute(query)
    signup = result.scalar_one_or_none()
    
    if signup:
        return {"is_signed_up": True}
        
    # Fallback: Check UserAction (in case of legacy data before migration)
    # Logic: Signed Up if there is a 'webinar_signup' event AND no newer 'webinar_unsignup' event.
    query_actions = select(UserAction).where(
        UserAction.user_id == current_user.id,
        UserAction.action.in_(["webinar_signup", "webinar_unsignup"])
    ).order_by(UserAction.created_at)
    
    result_actions = await db.execute(query_actions)
    actions = result_actions.scalars().all()
    
    last_status = "none" # none, signed_up, unsigned_up
    
    for action in actions:
        # Check if action relates to this webinar
        if action.payload and str(action.payload.get("webinar_id")) == str(webinar_id):
            if action.action == "webinar_signup":
                last_status = "signed_up"
            elif action.action == "webinar_unsignup":
                last_status = "unsigned_up"
                
    if last_status == "signed_up":
        # Sync it! (Autofix lazy migration)
        try:
            new_signup = WebinarSignup(
                user_id=current_user.id,
                webinar_id=webinar_id
            )
            db.add(new_signup)
            await db.commit()
        except:
            pass # Ignore race conditions
        return {"is_signed_up": True}

    return {"is_signed_up": False}

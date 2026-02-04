from typing import List, Optional, Union
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from models import User, UserRole, UserAction, WebinarSignup, WebinarSchedule, WebinarLibrary
from dependencies import get_current_user, get_db

router = APIRouter(prefix="/webinars", tags=["webinars"])

# === DTOs (Data Transfer Objects) ===

class WebinarBase(BaseModel):
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    speaker_name: Optional[str] = None

class WebinarScheduleBase(WebinarBase):
    connection_link: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int = 60

class WebinarLibraryBase(WebinarBase):
    video_url: str
    transcript_context: Optional[str] = ""
    conducted_at: datetime

class WebinarScheduleResponse(WebinarScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_upcoming: bool = True

    class Config:
        from_attributes = True

class WebinarLibraryResponse(WebinarLibraryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_upcoming: bool = False

    class Config:
        from_attributes = True

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

@router.get("", response_model=List[dict])
async def list_webinars(
    filter_type: str = Query("all", enum=["all", "library", "upcoming"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список вебинаров.
    filter_type:
      - 'library': только из библиотеки (WebinarLibrary)
      - 'upcoming': только из расписания (WebinarSchedule)
      - 'all': и те и другие (для админки или общих списков)
    """
    webinars = []
    
    if filter_type in ["all", "upcoming"]:
        query_schedule = select(WebinarSchedule).order_by(WebinarSchedule.scheduled_at)
        if current_user.role != UserRole.ADMIN:
            query_schedule = query_schedule.where(WebinarSchedule.is_published == True)
        
        res_schedule = await db.execute(query_schedule)
        schedules = res_schedule.scalars().all()
        # Add a flag for frontend differentiation
        for s in schedules:
            d = WebinarScheduleResponse.model_validate(s).model_dump()
            d["is_upcoming"] = True
            webinars.append(d)

    if filter_type in ["all", "library"]:
        query_library = select(WebinarLibrary).order_by(desc(WebinarLibrary.conducted_at))
        if current_user.role != UserRole.ADMIN:
            query_library = query_library.where(WebinarLibrary.is_published == True)
        
        res_library = await db.execute(query_library)
        libraries = res_library.scalars().all()
        for l in libraries:
            d = WebinarLibraryResponse.model_validate(l).model_dump()
            d["is_upcoming"] = False
            webinars.append(d)

    return webinars

@router.get("/upcoming/{webinar_id}", response_model=WebinarScheduleResponse)
async def get_upcoming_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить вебинар из расписания по ID"""
    webinar = await db.get(WebinarSchedule, webinar_id)
    if not webinar or (current_user.role != UserRole.ADMIN and not webinar.is_published):
        raise HTTPException(status_code=404, detail="Webinar not found")
    return webinar

@router.get("/library/{webinar_id}", response_model=WebinarLibraryResponse)
async def get_library_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить вебинар из библиотеки по ID"""
    webinar = await db.get(WebinarLibrary, webinar_id)
    if not webinar or (current_user.role != UserRole.ADMIN and not webinar.is_published):
        raise HTTPException(status_code=404, detail="Webinar not found")
    return webinar

@router.get("/{webinar_id}", response_model=Union[WebinarScheduleResponse, WebinarLibraryResponse])
async def get_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить один вебинар по ID (ищет в обоих таблицах)"""
    # 1. Try Schedule
    schedule = await db.get(WebinarSchedule, webinar_id)
    if schedule:
        if current_user.role != UserRole.ADMIN and not schedule.is_published:
             raise HTTPException(status_code=404, detail="Webinar not found")
        return schedule

    # 2. Try Library
    library = await db.get(WebinarLibrary, webinar_id)
    if library:
        if current_user.role != UserRole.ADMIN and not library.is_published:
             raise HTTPException(status_code=404, detail="Webinar not found")
        return library

    raise HTTPException(status_code=404, detail="Webinar not found")

@router.post("", response_model=Union[WebinarScheduleResponse, WebinarLibraryResponse])
async def create_webinar(
    webinar_data: WebinarUpdate, # Use loose schema to accept all fields
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Создать новый вебинар"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    data = webinar_data.model_dump(exclude_unset=True)
    is_upcoming = data.get("is_upcoming", False)
    
    if is_upcoming:
        # Create Schedule
        new_item = WebinarSchedule(**data)
        if not new_item.scheduled_at:
             new_item.scheduled_at = datetime.utcnow()
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        return new_item
    else:
        # Create Library
        new_item = WebinarLibrary(**data)
        if "video_url" not in data:
            new_item.video_url = ""
        if not new_item.conducted_at:
             new_item.conducted_at = datetime.utcnow()
        
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        return new_item

@router.patch("/{webinar_id}", response_model=Union[WebinarScheduleResponse, WebinarLibraryResponse])
async def update_webinar(
    webinar_id: int,
    update_data: WebinarUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Обновить вебинар"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Try Schedule
    schedule = await db.get(WebinarSchedule, webinar_id)
    if schedule:
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        schedule.updated_at = datetime.utcnow()
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    # Try Library
    library = await db.get(WebinarLibrary, webinar_id)
    if library:
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
             if hasattr(library, key):
                setattr(library, key, value)
        library.updated_at = datetime.utcnow()
        db.add(library)
        await db.commit()
        await db.refresh(library)
        return library

    raise HTTPException(status_code=404, detail="Webinar not found")

@router.delete("/{webinar_id}")
async def delete_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Удалить вебинар"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Try Schedule
    schedule = await db.get(WebinarSchedule, webinar_id)
    if schedule:
        await db.delete(schedule)
        await db.commit()
        return {"status": "deleted", "id": webinar_id, "type": "schedule"}

    # Try Library
    library = await db.get(WebinarLibrary, webinar_id)
    if library:
        await db.delete(library)
        await db.commit()
        return {"status": "deleted", "id": webinar_id, "type": "library"}

    raise HTTPException(status_code=404, detail="Webinar not found")


# === Signup Endpoints (Dual Write: UserAction + WebinarSignup) ===

@router.post("/{webinar_id}/signup")
async def signup_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Записаться на вебинар (Dual Write: History + Notification Queue)"""
    # 1. Check if webinar exists in schedule
    webinar = await db.get(WebinarSchedule, webinar_id)
    if not webinar:
        raise HTTPException(status_code=404, detail="Upcoming webinar not found")

    # 2. Check if already signed up
    query_signup = select(WebinarSignup).where(
        WebinarSignup.user_id == current_user.id,
        WebinarSignup.schedule_id == webinar_id
    )
    result_signup = await db.execute(query_signup)
    existing_signup = result_signup.scalar_one_or_none()
    
    if existing_signup:
         return {"status": "already_signed_up"}

    # 3. Create Notification Entry (WebinarSignup)
    new_signup = WebinarSignup(
        user_id=current_user.id,
        schedule_id=webinar_id
    )
    db.add(new_signup)
    
    # 4. Create Audit Log (UserAction)
    new_action = UserAction(
        user_id=current_user.id,
        action="webinar_signup",
        payload={"schedule_id": webinar_id}
    )
    db.add(new_action)
    
    await db.commit()
    return {"status": "signed_up", "schedule_id": webinar_id}

@router.delete("/{webinar_id}/signup")
async def cancel_signup_webinar(
    webinar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отменить запись"""
    # 1. Delete from Notification Queue
    query_signup = select(WebinarSignup).where(
        WebinarSignup.user_id == current_user.id,
        WebinarSignup.schedule_id == webinar_id
    )
    result_signup = await db.execute(query_signup)
    signup = result_signup.scalar_one_or_none()
    
    if signup:
        await db.delete(signup)

    # 2. Add 'webinar_unsignup' event to Audit Log (Preserve History)
    unsignup_action = UserAction(
        user_id=current_user.id,
        action="webinar_unsignup",
        payload={"schedule_id": webinar_id}
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
    """Проверить, записан ли пользователь"""
    query = select(WebinarSignup).where(
        WebinarSignup.user_id == current_user.id,
        WebinarSignup.schedule_id == webinar_id
    )
    result = await db.execute(query)
    signup = result.scalar_one_or_none()
    
    if signup:
        return {"is_signed_up": True}
        
    # Fallback: Check UserAction
    query_actions = select(UserAction).where(
        UserAction.user_id == current_user.id,
        UserAction.action.in_(["webinar_signup", "webinar_unsignup"])
    ).order_by(UserAction.created_at)
    
    result_actions = await db.execute(query_actions)
    actions = result_actions.scalars().all()
    
    last_status = "none"
    
    for action in actions:
        if action.payload and str(action.payload.get("schedule_id")) == str(webinar_id):
            if action.action == "webinar_signup":
                last_status = "signed_up"
            elif action.action == "webinar_unsignup":
                last_status = "unsigned_up"
                
    if last_status == "signed_up":
        try:
            new_signup = WebinarSignup(
                user_id=current_user.id,
                schedule_id=webinar_id
            )
            db.add(new_signup)
            await db.commit()
        except:
            pass
        return {"is_signed_up": True}

    return {"is_signed_up": False}

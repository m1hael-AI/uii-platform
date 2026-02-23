from typing import List, Optional, Union
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from models import User, UserRole, UserAction, WebinarSignup, WebinarSchedule, WebinarLibrary
from dependencies import get_current_user, get_db
from services.video_service import process_video_thumbnail

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
    
    # Unified Fields
    type: str = "webinar"
    program: Optional[List[dict]] = None # JSON list of sub-events
    landing_bullets: Optional[List[str]] = None # JSON list of bullets

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
    
    # Unified Fields
    type: Optional[str] = None
    program: Optional[List[dict]] = None
    landing_bullets: Optional[List[str]] = None

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


# === AI Search Config ===
SEARCH_VECTOR_LIMIT = 20      # Кол-во кандидатов от векторного поиска
SEARCH_RERANK_MODEL = "gpt-4.1-mini"

RERANK_PROMPT = """Ты — помощник, который оценивает релевантность вебинаров поисковому запросу.

Запрос пользователя: "{query}"

Список вебинаров (JSON):
{webinars_json}

Верни ТОЛЬКО JSON со списком ID вебинаров, которые реально отвечают на запрос.
Если вебинар лишь косвенно связан или вообще не связан — не включай его.
Формат ответа (строго JSON, без лишнего текста):
{{"relevant_ids": [1, 3, 7]}}"""


@router.get("/search", response_model=List[dict])
async def ai_search_webinars(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    AI-поиск по библиотеке вебинаров.
    1. Векторный поиск по title+description (cosine similarity)
    2. LLM Re-ranking через gpt-4.1-mini
    3. Fallback на текстовый поиск (логируется)
    """
    from services.openai_service import generate_embedding
    from sqlalchemy import func
    import json
    from openai import AsyncOpenAI
    import os
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    logger_local = __import__("loguru").logger
    
    base_query = select(WebinarLibrary)
    if current_user.role != UserRole.ADMIN:
        base_query = base_query.where(WebinarLibrary.is_published == True)
    
    candidates: list[WebinarLibrary] = []
    used_fallback = False
    
    # === Шаг 1: Векторный поиск ===
    try:
        query_embedding = await generate_embedding(q)
        
        # Ищем вебинары у которых search_embedding не NULL
        vector_query = base_query.where(
            WebinarLibrary.search_embedding != None
        ).order_by(
            WebinarLibrary.search_embedding.cosine_distance(query_embedding)
        ).limit(SEARCH_VECTOR_LIMIT)
        
        result = await db.execute(vector_query)
        candidates = result.scalars().all()
        
    except Exception as e:
        logger_local.error(f"❌ WebinarSearch: vector search failed: {e}")
        candidates = []
    
    # === Fallback: Текстовый поиск ===
    if not candidates:
        logger_local.warning(
            f"⚠️ WebinarSearch: falling back to text search for query: '{q}' "
            f"(reason: no embeddings or vector search error)"
        )
        used_fallback = True
        
        text_query = base_query.where(
            WebinarLibrary.title.ilike(f"%{q}%")
        ).order_by(WebinarLibrary.conducted_at.desc()).limit(SEARCH_VECTOR_LIMIT)
        
        result = await db.execute(text_query)
        candidates = result.scalars().all()
        
        # Конвертируем и возвращаем без LLM (текстовый поиск сам по себе точный)
        output = []
        for w in candidates:
            d = WebinarLibraryResponse.model_validate(w).model_dump()
            d["is_upcoming"] = False
            output.append(d)
        return output
    
    if not candidates:
        return []
    
    # === Шаг 2: LLM Re-ranking ===
    webinars_for_llm = [
        {
            "id": w.id,
            "title": w.title,
            "short_description": w.short_description or (w.description[:200] if w.description else "Нет описания")
        }
        for w in candidates
    ]
    
    try:
        prompt = RERANK_PROMPT.format(
            query=q,
            webinars_json=json.dumps(webinars_for_llm, ensure_ascii=False, indent=2)
        )
        
        response = await client.chat.completions.create(
            model=SEARCH_RERANK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        llm_output = json.loads(response.choices[0].message.content)
        relevant_ids = set(llm_output.get("relevant_ids", []))
        
        logger_local.info(
            f"🔍 WebinarSearch: query='{q}', candidates={len(candidates)}, "
            f"relevant_after_rerank={len(relevant_ids)}"
        )
        
        # Фильтруем и сохраняем порядок из LLM (relevant_ids — приоритет)
        id_to_webinar = {w.id: w for w in candidates}
        ranked_webinars = [id_to_webinar[wid] for wid in relevant_ids if wid in id_to_webinar]
        
    except Exception as e:
        logger_local.error(f"❌ WebinarSearch: LLM re-ranking failed, returning all candidates: {e}")
        ranked_webinars = candidates
    
    # Собираем ответ
    output = []
    for w in ranked_webinars:
        d = WebinarLibraryResponse.model_validate(w).model_dump()
        d["is_upcoming"] = False
        output.append(d)
    
    return output


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

@router.get("/join/{webinar_id}")
async def join_webinar_smart_link(
    webinar_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Умный редирект для входа на вебинар/спринт.
    - Если это обычный вебинар -> редирект на connection_link
    - Если это Спринт -> ищет актуальный урок по дате и редиректит на него
    """
    from fastapi.responses import RedirectResponse
    
    # 1. Get Webinar
    webinar = await db.get(WebinarSchedule, webinar_id)
    if not webinar:
        raise HTTPException(status_code=404, detail="Webinar not found")
        
    # 2. Check Type
    target_link = webinar.connection_link
    
    if webinar.type == "sprint" and webinar.program:
        # Logic: Find the "current" or "next" event in the program
        now = datetime.utcnow()
        # Program structure expected: [{"date": "ISO", "link": "url", "title": "..."}]
        
        # Sort program by date just in case
        try:
            program_sorted = sorted(webinar.program, key=lambda x: x.get("date", ""))
            
            # Find first event that hasn't finished (assuming 2h duration for safety)
            for event in program_sorted:
                event_date = datetime.fromisoformat(event.get("date").replace("Z", "+00:00"))
                # If event starts in future or started less than 3 hours ago -> It's the one
                # Simple logic: Redirect to the first one that is "Today/Now" or "Future"
                
                # If event is in the past (more than 4 hours ago), skip
                time_diff = (now - event_date.replace(tzinfo=None)).total_seconds()
                
                # If event is in future (negative diff) OR event started recently (< 4 hours)
                if time_diff < 4 * 3600:
                    if event.get("link"):
                        target_link = event.get("link")
                        break
        except Exception as e:
            # Fallback to main link if date parsing fails
            pass

    if not target_link:
         raise HTTPException(status_code=404, detail="Link not found")
         
    return RedirectResponse(target_link)

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

async def _process_thumbnail_task(webinar_id: int, video_url: str, is_schedule: bool):
    """Background task to fetch, download and upload thumbnail to S3."""
    from database import async_session_factory
    
    s3_url = await process_video_thumbnail(video_url)
    if s3_url:
        async with async_session_factory() as db:
            if is_schedule:
                item = await db.get(WebinarSchedule, webinar_id)
            else:
                item = await db.get(WebinarLibrary, webinar_id)
            
            if item:
                item.thumbnail_url = s3_url
                item.updated_at = datetime.utcnow()
                db.add(item)
                await db.commit()

@router.post("", response_model=Union[WebinarScheduleResponse, WebinarLibraryResponse])
async def create_webinar(
    webinar_data: WebinarUpdate, # Use loose schema to accept all fields
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Создать новый вебинар"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    data = webinar_data.model_dump(exclude_unset=True)
    is_upcoming = data.get("is_upcoming", False)
    video_url = data.get("video_url")
    thumbnail_url = data.get("thumbnail_url")
    
    # Remove control field from data before creating DB model
    if "is_upcoming" in data:
        del data["is_upcoming"]

    if is_upcoming:
        # Create Schedule
        new_item = WebinarSchedule(**data)
        if not new_item.scheduled_at:
             new_item.scheduled_at = datetime.utcnow()
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        
        # Background thumbnail processing
        if video_url and not thumbnail_url:
             background_tasks.add_task(_process_thumbnail_task, new_item.id, video_url, True)
             
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

        # Background thumbnail processing
        if new_item.video_url and not thumbnail_url:
             background_tasks.add_task(_process_thumbnail_task, new_item.id, new_item.video_url, False)

        return new_item

@router.patch("/{webinar_id}", response_model=Union[WebinarScheduleResponse, WebinarLibraryResponse])
async def update_webinar(
    webinar_id: int,
    update_data: WebinarUpdate,
    background_tasks: BackgroundTasks,
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
        old_video = schedule.thumbnail_url # Just checking for comparison
        for key, value in data.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        schedule.updated_at = datetime.utcnow()
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)

        # If video_url changed or thumbnail is missing, trigger re-process
        if schedule.connection_link and not schedule.thumbnail_url:
             # For schedule we might use connection_link or some other field if it's a video link
             pass # Logic depends on how schedule handles videos
             
        return schedule

    # Try Library
    library = await db.get(WebinarLibrary, webinar_id)
    if library:
        data = update_data.model_dump(exclude_unset=True)
        video_changed = "video_url" in data and data["video_url"] != library.video_url
        thumbnail_missing = not library.thumbnail_url and not data.get("thumbnail_url")
        
        for key, value in data.items():
             if hasattr(library, key):
                setattr(library, key, value)
        
        library.updated_at = datetime.utcnow()
        db.add(library)
        await db.commit()
        await db.refresh(library)

        if (video_changed or thumbnail_missing) and library.video_url:
             background_tasks.add_task(_process_thumbnail_task, library.id, library.video_url, False)

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

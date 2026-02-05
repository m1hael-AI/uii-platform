from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from datetime import datetime

from services.openai_service import generate_chat_response, stream_chat_response
from services.context_manager import is_context_overflow, compress_context_task
from dependencies import get_db, get_current_user
from models import User, ChatSession, Message, MessageRole, Agent, PendingAction, WebinarLibrary, WebinarSchedule

router = APIRouter(prefix="/chat", tags=["chat"])

# --- GREETINGS MAPPING ---
GREETINGS = {
    "mentor": "Привет! Я твой персональный куратор. Я здесь, чтобы помочь тебе освоиться на платформе, ответить на вопросы по обучению и поддержать тебя на пути к новой профессии. С чего начнем?",
    "python": "Привет! Я помогу разобраться с Python, кодом и архитектурой. Есть вопросы по домашке?",
    "hr": "Привет! Я помогу подготовиться к собеседованию и составить резюме. Расскажи о своем опыте?",
    "analyst": "Привет! Если нужно проанализировать данные или разобраться с Pandas — я здесь. Посмотрим на твои цифры?"
}


# Request Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage] 
    agent_id: Optional[str] = "mentor"
    webinar_id: Optional[int] = None

# History Response Model
class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: str

class HistoryResponse(BaseModel):
    messages: List[HistoryMessage]
    last_read_at: Optional[str] = None

class ChatSessionDTO(BaseModel):
    id: int
    agent_id: str
    agent_name: str
    agent_avatar: Optional[str]
    last_message_at: Optional[str]
    has_unread: bool = False

async def ensure_initial_sessions(db: AsyncSession, user_id: int):
    """
    Ensures that a new user has all necessary initial sessions (Mentor, Python, etc. + Assistant)
    Created here to be called from both /sessions and /unread-status for instant cold start.
    """
    # 1. Check if user already has sessions
    q = select(ChatSession).where(ChatSession.user_id == user_id)
    res = await db.execute(q)
    if res.first():
        return False # Already has sessions
        
    # 2. Setup initial sessions
    initial_slugs = ["mentor", "python", "hr", "analyst", "main_assistant"]
    
    for slug in initial_slugs:
        # For agents, check existence. Assistant is a special slug.
        if slug != "main_assistant":
            agent_res = await db.execute(select(Agent).where(Agent.slug == slug))
            agent_obj = agent_res.scalar_one_or_none()
            if not agent_obj: continue
        
        # Create Session
        new_session = ChatSession(
            user_id=user_id,
            agent_slug=slug,
            is_active=True,
            last_message_at=datetime.utcnow(),
            last_read_at=datetime(2000, 1, 1) # Force unread
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        # Create Welcome Message
        welcome_text = GREETINGS.get(slug, "Здравствуйте! Я ваш AI-помощник. Чем могу помочь?")
        if slug == "main_assistant":
             welcome_text = "Здравствуйте! Я ваш AI-помощник. Я всегда под рукой в боковой панели, чтобы помочь с любым вопросом. С чего начнем?"
        
        msg = Message(
            session_id=new_session.id,
            role=MessageRole.ASSISTANT,
            content=welcome_text,
            created_at=datetime.utcnow()
        )
        db.add(msg)
        await db.commit()
    
    return True

@router.get("/sessions", response_model=List[ChatSessionDTO])
async def get_user_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks() # Add BackgoundTasks
):
    """Get all active chat sessions for the user with last message preview"""
    # 1. Get all sessions for user (excluding specific webinar chats if any, or including?)
    # Usually sidebar shows Agent chats. Webinar chats might be separate or same.
    # Let's include everything that is NOT bound to a specific webinar (general agent chats)
    # OR all valid sessions. The frontend list seems to be Agents.
    
    q = select(ChatSession, Agent).join(Agent, ChatSession.agent_slug == Agent.slug).where(
        ChatSession.user_id == current_user.id,
        ChatSession.is_active == True,
        ChatSession.schedule_id == None,
        ChatSession.library_id == None # Only general agent chats
    ).order_by(ChatSession.last_message_at.desc())
    
    result = await db.execute(q)
    rows = result.all() # [(ChatSession, Agent), ...]
    
    if not rows:
        # --- COLD START LOGIC ---
        await ensure_initial_sessions(db, current_user.id)
        # Re-fetch rows (exclude assistant from the main list if desired, but previously it seemed we wanted them?)
        # Wait, the frontend list usually DOES NOT show the main assistant if it's in the sidebar.
        # But for notification "bell" we check all.
        # For this endpoint /sessions which powers the "Agents" page, we typically exclude main_assistant if it lives in sidebar only.
        # The previous code had `q.where(ChatSession.agent_slug != "main_assistant")`. Let's keep that constraint if it was there.
        # Actually in the VERY first version it didn't filtering.
        # But in Step 405 replacement it added filtering. 
        # Let's apply filtering to be safe as per previous intent.
        
        q_agents = q.where(ChatSession.agent_slug != "main_assistant")
        result = await db.execute(q_agents)
        rows = result.all()
    else:
        # If we had rows initially, we might still want to filter main_assistant if it was returned by general query?
        # The general query joins Agent. 
        # If main_assistant is in Agent table, it might appear.
        # Let's filter it out in python or query to be consistent.
        rows = [r for r in rows if r[0].agent_slug != "main_assistant"]

    sessions_dto = []
    
    for session, agent in rows:
        # Get last message content
        msg_q = select(Message).where(Message.session_id == session.id).order_by(Message.created_at.desc()).limit(1)
        msg_res = await db.execute(msg_q)
        last_msg = msg_res.scalar_one_or_none()
        
        last_content = last_msg.content if last_msg else "Начните диалог"
        if len(last_content) > 60:
            last_content = last_content[:60] + "..."
            
        # Red dot logic
        has_unread = False
        if session.last_message_at:
            if not session.last_read_at:
                has_unread = True
            elif session.last_message_at > session.last_read_at:
                has_unread = True

        sessions_dto.append(ChatSessionDTO(
            id=session.id,
            agent_id=agent.slug,
            agent_name=agent.name,
            agent_avatar=agent.avatar_url,
            last_message=last_content,
            last_message_at=session.last_message_at.isoformat() if session.last_message_at else None,
            has_unread=has_unread
        ))
        
    return sessions_dto

@router.get("/history", response_model=HistoryResponse)
async def get_chat_history(
    webinar_id: Optional[int] = None,
    agent_id: Optional[str] = "mentor",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat history for current user and context"""
    q = select(ChatSession).where(
        ChatSession.user_id == current_user.id
    )
    
    if webinar_id is not None:
        # Check both tables as ID might refer to either (assuming ID collision risk is handled or acceptable for now)
        q = q.where(or_(ChatSession.library_id == webinar_id, ChatSession.schedule_id == webinar_id))
    else:
        # If no webinar, stick to agent slug AND ensure it's not a webinar session
        q = q.where(ChatSession.agent_slug == agent_id).where(ChatSession.schedule_id == None, ChatSession.library_id == None)
        
    result = await db.execute(q)
    session = result.scalar_one_or_none()
    
    if not session:
        return HistoryResponse(messages=[])
        
    # Get messages
    msgs_q = select(Message).where(Message.session_id == session.id).order_by(Message.created_at)
    res = await db.execute(msgs_q)
    messages = res.scalars().all()
    
    return HistoryResponse(
        messages=[
            HistoryMessage(
                role=m.role.value, 
                content=m.content, 
                created_at=m.created_at.isoformat()
            ) for m in messages
        ],
        last_read_at=session.last_read_at.isoformat() if session.last_read_at else None
    )

@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Get Webinar Context
    webinar_context = ""
    if request.webinar_id:
        # Try retrieving context from WebinarLibrary (most likely source of transcripts)
        res = await db.execute(select(WebinarLibrary).where(WebinarLibrary.id == request.webinar_id))
        w = res.scalar_one_or_none()
        if w and w.transcript_context:
            webinar_context = w.transcript_context
        else:
            # Fallback (rare): try Schedule, though likely no transcript yet
            res_sch = await db.execute(select(WebinarSchedule).where(WebinarSchedule.id == request.webinar_id))
            w_sch = res_sch.scalar_one_or_none()
            if w_sch and hasattr(w_sch, 'transcript_context') and w_sch.transcript_context:
                 webinar_context = w_sch.transcript_context

    # 2. Get or Create Session
    q = select(ChatSession).where(ChatSession.user_id == current_user.id)
    if request.webinar_id is not None:
        # Try to match either
        q = q.where(or_(ChatSession.library_id == request.webinar_id, ChatSession.schedule_id == request.webinar_id))
    else:
        slug = request.agent_id or "mentor"
        q = q.where(ChatSession.agent_slug == slug).where(ChatSession.schedule_id == None, ChatSession.library_id == None)
        
    result = await db.execute(q)
    chat_session = result.scalar_one_or_none()
    
    if not chat_session:
        # Create new session
        slug = request.agent_id or "mentor"
        
        # Determine strict type for creation
        schedule_id = None
        library_id = None
        
        if request.webinar_id:
            # We already did lookup in step 1. Check which context was found.
            # However, step 1 var 'webinar_context' doesn't tell us WHICH one was found.
            # Let's re-verify to be safe for foreign keys.
            
            # Check Library first (as per Step 1 precedence)
            res = await db.execute(select(WebinarLibrary).where(WebinarLibrary.id == request.webinar_id))
            lib = res.scalar_one_or_none()
            if lib:
                library_id = lib.id
            else:
                # Check Schedule
                res_sch = await db.execute(select(WebinarSchedule).where(WebinarSchedule.id == request.webinar_id))
                sch = res_sch.scalar_one_or_none()
                if sch:
                    schedule_id = sch.id
        
        chat_session = ChatSession(
            user_id=current_user.id,
            agent_slug=slug,
            schedule_id=schedule_id,
            library_id=library_id,
            is_active=True
        )
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)
        
        # --- AUTO GREETING ---
        # Fetch agent name for greeting
        agent_res = await db.execute(select(Agent).where(Agent.slug == slug))
        agent_obj = agent_res.scalar_one_or_none()
        agent_name = agent_obj.name if agent_obj else "AI Assistant"
        
        greeting_text = GREETINGS.get(slug, f"Привет! Я {agent_name}. Чем могу помочь?")
            
        greeting_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.ASSISTANT,
            content=greeting_text
        )
        db.add(greeting_msg)
        
        # Set last_message_at so it appears at top
        chat_session.last_message_at = datetime.utcnow()
        # Set last_read_at in the past so it's unread
        chat_session.last_read_at = datetime(2000, 1, 1)
        
        await db.commit()
        # ---------------------

    # 3. Save User Message
    # We take the LAST message from the client as the new one
    if request.messages:
        last_user_msg_content = request.messages[-1].content
        user_db_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.USER,
            content=last_user_msg_content
        )
        db.add(user_db_msg)
        
        # ⏰ Update last_message_at for proactivity timer
        chat_session.last_message_at = datetime.utcnow()
        
        # 🔪 Kill Switch: Delete pending proactive tasks for this agent
        # If user initiates conversation, we don't need to send proactive message
        agent_slug = request.agent_id or "mentor"
        await db.execute(
            delete(PendingAction)
            .where(PendingAction.user_id == current_user.id)
            .where(PendingAction.agent_slug == agent_slug)
            .where(PendingAction.status == "pending")
        )
        
        await db.commit()

    # 4. Prepare Prompt
    system_prompt = "You are a helpful AI Assistant."

    if webinar_context:
        system_prompt = (
            f"Ты — виртуальный ассистент по вебинару.\n"
            f"Используй ТОЛЬКО следующий текст для ответа на вопросы:\n"
            f"--- НАЧАЛО ТЕКСТА ---\n"
            f"{webinar_context[:150000]}\n" # Safety truncation
            f"--- КОНЕЦ ТЕКСТА ---\n"
            f"Если ответа нет в тексте, скажи об этом вежливо."
        )
    else:
        # Load agent from DB
        agent_slug = request.agent_id or "mentor"
        agent_res = await db.execute(select(Agent).where(Agent.slug == agent_slug))
        agent_obj = agent_res.scalar_one_or_none()
        if agent_obj and agent_obj.system_prompt:
            system_prompt = agent_obj.system_prompt

    conversation = [{"role": "system", "content": system_prompt}]
    for m in request.messages:
        conversation.append({"role": m.role, "content": m.content})
        
    # --- Context Management Check ---
    # Получаем настройки из БД
    from services.settings_service import get_proactivity_settings
    settings = await get_proactivity_settings(db)
    
    current_model = settings.model # Используем модель из настроек!
    
    # Проверяем переполнение
    if is_context_overflow(
        conversation, 
        max_tokens=settings.context_soft_limit, 
        threshold=settings.context_threshold, 
        model=current_model
    ):
        background_tasks.add_task(
            compress_context_task, 
            session_id=chat_session.id, 
            keep_last_n=settings.context_compression_keep_last,
            model=current_model
        )
        
    # 5. Stream & Save
    async def response_generator():
        full_response = ""
        try:
            async for chunk in stream_chat_response(conversation, max_tokens=1500):
                full_response += chunk
                yield chunk
        except Exception as e:
            print(f"Stream error: {e}")
            yield f"[Error: {str(e)}]"
        finally:
             if full_response:
                 try:
                     # Create a new local saving logic because 'db' might be closed or detached
                     # Actually asyncpg connection might be closed by FastAPI.
                     # We reuse 'db' and try. If it fails, we ignore log.
                     ai_msg = Message(
                         session_id=chat_session.id,
                         role=MessageRole.ASSISTANT,
                         content=full_response
                     )
                     db.add(ai_msg)
                     
                     # ⏰ Update last_message_at for proactivity timer
                     chat_session.last_message_at = datetime.utcnow()
                     
                     await db.commit()
                 except Exception as ex:
                     print(f"Failed to save AI history: {ex}")

    return StreamingResponse(
        response_generator(), 
        media_type="text/event-stream", 
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Prevent Nginx/Proxy buffering
        }
    )

@router.post("/read")
async def mark_chat_read(
    webinar_id: Optional[int] = None,
    agent_id: Optional[str] = "mentor",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark chat session as read (update last_read_at)"""
    q = select(ChatSession).where(ChatSession.user_id == current_user.id)
    
    if webinar_id is not None:
        q = q.where(or_(ChatSession.library_id == webinar_id, ChatSession.schedule_id == webinar_id))
    else:
        q = q.where(ChatSession.agent_slug == agent_id, ChatSession.library_id == None, ChatSession.schedule_id == None)
        
    result = await db.execute(q)
    session = result.scalar_one_or_none()
    
    if not session:
        # Session not found - nothing to mark read yet
        return {"status": "ok", "message": "No session found"}
        
    session.last_read_at = datetime.utcnow()
    await db.commit()
    
    return {"status": "ok", "last_read_at": session.last_read_at.isoformat()}


@router.post("/test/reset")
async def reset_user_chats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    DEV TOOLS: Reset all chat history for the current user.
    Used to test 'Cold Start' user experience.
    """
    # 1. Find all active sessions for this user
    q = select(ChatSession.id).where(ChatSession.user_id == current_user.id)
    result = await db.execute(q)
    session_ids = result.scalars().all()
    
    if not session_ids:
        return {"status": "ok", "message": "Nothing to reset"}
        
    # 2. Delete Messages first (FK constraint)
    # Using delete() statement for bulk deletion
    await db.execute(delete(Message).where(Message.session_id.in_(session_ids)))
    
    # 3. Delete Sessions
    await db.execute(delete(ChatSession).where(ChatSession.id.in_(session_ids)))
    
    # 4. Clear Pending Actions (Proactivity)
    await db.execute(delete(PendingAction).where(PendingAction.user_id == current_user.id))
    
    await db.commit()
    
    return {"status": "ok", "message": f"Reset complete. Deleted {len(session_ids)} sessions."}


@router.get("/unread-status")
async def get_unread_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if there are ANY unread messages across all user sessions.
    Used for the global header bell icon.
    """
    # 0. Trigger Cold Start if needed (Ensures notifications work on first layout load)
    await ensure_initial_sessions(db, current_user.id)

    # 1. Check Agent sessions
    q = select(ChatSession).where(
        ChatSession.user_id == current_user.id,
        ChatSession.is_active == True,
        or_(
            ChatSession.last_read_at == None,
            ChatSession.last_message_at > ChatSession.last_read_at
        )
    )
    res = await db.execute(q)
    any_unread = res.first() is not None
    
    return {"has_unread": any_unread}


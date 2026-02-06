from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, or_, update
from datetime import datetime
import asyncio
import json
import logging
import yaml
from pathlib import Path

from services.openai_service import generate_chat_response, stream_chat_response
from services.context_manager import is_context_overflow, compress_context_task
from dependencies import get_db, get_current_user, rate_limiter
from models import User, ChatSession, Message, MessageRole, Agent, PendingAction, WebinarLibrary, WebinarSchedule
from config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

# Create AsyncSessionLocal for background tasks
database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
bg_engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(bg_engine, class_=AsyncSession, expire_on_commit=False)

# --- GREETINGS MAPPING ---
# --- GREETINGS MAPPING ---
def load_greetings():
    try:
        path = Path(__file__).parent.parent / "resources" / "default_prompts.yaml"
        if not path.exists():
            print(f"WARNING: Prompts file not found at {path}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Transform to simple dict {slug: greeting}
        agents = data.get("agents", {})
        return {slug: props.get("greeting") for slug, props in agents.items() if props.get("greeting")}
    except Exception as e:
        print(f"Error loading greetings: {e}")
        return {}

GREETINGS = load_greetings()

# --- SSE NOTIFICATION MANAGER ---
class NotificationManager:
    def __init__(self):
        # user_id -> set of queues (one per connection/tab)
        self.connections: dict[int, set[asyncio.Queue]] = {}

    async def connect(self, user_id: int) -> asyncio.Queue:
        if user_id not in self.connections:
            self.connections[user_id] = set()
        queue = asyncio.Queue()
        self.connections[user_id].add(queue)
        print(f"SSE: User {user_id} connected. Active tabs: {len(self.connections[user_id])}")
        return queue

    def disconnect(self, user_id: int, queue: asyncio.Queue):
        if user_id in self.connections:
            self.connections[user_id].discard(queue)
            if not self.connections[user_id]:
                del self.connections[user_id]
        print(f"SSE: User {user_id} disconnected.")

    async def broadcast(self, user_id: int, message: dict):
        """Send message to all open tabs of a user"""
        if user_id not in self.connections:
            return
            
        # Serialize once
        data = f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
        
        # Send to all queues
        for queue in self.connections[user_id]:
            await queue.put(data)
            
manager = NotificationManager()


# Request Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage] 
    agent_id: Optional[str] = "mentor"
    webinar_id: Optional[int] = None
    save_user_message: bool = True # Control duplication

# History Response Model
class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: str

class HistoryResponse(BaseModel):
    messages: List[HistoryMessage]
    last_read_at: Optional[str] = None
    is_new_session: bool = False  # True if session has no messages (even archived)

class ChatSessionDTO(BaseModel):
    id: int
    agent_id: str
    agent_name: str
    agent_avatar: Optional[str]
    last_message: str # FIX: Added back
    last_message_at: Optional[str]
    has_unread: bool = False

async def ensure_initial_sessions(db: AsyncSession, user_id: int):
    """
    Ensures that a new user has all necessary initial sessions (Agents + Assistant)
    Created here to be called from both /sessions and /unread-status for instant cold start.
    
    NOTE: Creates greeting messages for AGENTS immediately.
    Main Assistant greeting is created on-demand via /chat/history (with 1-second delay).
    """
    # 1. Check if user already has sessions
    q = select(ChatSession).where(ChatSession.user_id == user_id)
    res = await db.execute(q)
    if res.first():
        return False # Already has sessions
        
    # 2. Setup initial sessions
    initial_slugs = ["startup_expert", "python", "hr", "analyst", "main_assistant"]
    
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
            is_active=True
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        # Create greeting message for AGENTS (not for main_assistant)
        if slug != "main_assistant":
            welcome_text = agent_obj.greeting_message if agent_obj.greeting_message else GREETINGS.get(slug, "Привет! Чем могу помочь?")
            
            msg = Message(
                session_id=new_session.id,
                role=MessageRole.ASSISTANT,
                content=welcome_text,
                created_at=datetime.utcnow()
            )
            db.add(msg)
            
            # Update session timestamps
            new_session.last_message_at = datetime.utcnow()
            new_session.last_read_at = datetime(2000, 1, 1)  # Mark as unread
            
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
            last_message=last_content, # FIX: Passed correctly
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
        
    # Get messages (exclude archived and system messages)
    msgs_q = select(Message).where(
        Message.session_id == session.id,
        Message.is_archived == False,
        Message.role != MessageRole.SYSTEM
    ).order_by(Message.created_at)
    res = await db.execute(msgs_q)
    messages = res.scalars().all()
    
    # Check if this is a truly new session (no messages at all, even archived)
    all_msgs_q = select(Message).where(Message.session_id == session.id)
    all_msgs_res = await db.execute(all_msgs_q)
    all_messages = all_msgs_res.scalars().all()
    is_new_session = len(all_messages) == 0
    
    # If session exists but has NO messages (after filter), trigger delayed greeting
    # BUT only for non-AI-Tutor agents (AI Tutor greeting is handled by frontend)
    if len(messages) == 0 and agent_id and agent_id != "ai_tutor":
        # Trigger delayed greeting (1 second) for notification UX
        async def send_delayed_greeting():
            await asyncio.sleep(1)  # Wait 1 second
            
            # Create new DB session for background task
            async with AsyncSessionLocal() as bg_db:
                # Fetch agent name for greeting
                if agent_id != "main_assistant":
                    agent_res = await bg_db.execute(select(Agent).where(Agent.slug == agent_id))
                    agent_obj = agent_res.scalar_one_or_none()
                    agent_name = agent_obj.name if agent_obj else "AI Assistant"
                else:
                    agent_name = "AI Помощник"
                
                # Get greeting text
                if agent_id == "main_assistant":
                    greeting_text = "Здравствуйте! Я ваш AI-помощник. Я всегда под рукой в боковой панели, чтобы помочь с любым вопросом. С чего начнем?"
                else:
                    greeting_text = GREETINGS.get(agent_id, f"Привет! Я {agent_name}. Чем могу помочь?")
                    
                greeting_msg = Message(
                    session_id=session.id,
                    role=MessageRole.ASSISTANT,
                    content=greeting_text
                )
                bg_db.add(greeting_msg)
                
                # Update session timestamps
                session_stmt = select(ChatSession).where(ChatSession.id == session.id)
                session_result = await bg_db.execute(session_stmt)
                sess = session_result.scalar_one_or_none()
                if sess:
                    sess.last_message_at = datetime.utcnow()
                    sess.last_read_at = datetime(2000, 1, 1)  # Mark as unread
                
                await bg_db.commit()
                
                # 🔔 Notify User (New Greeting Message)
                await manager.broadcast(current_user.id, {"type": "chatStatusUpdate"})
        
        # Start background task (don't await)
        asyncio.create_task(send_delayed_greeting())
    
    return HistoryResponse(
        messages=[
            HistoryMessage(
                role=m.role.value, 
                content=m.content, 
                created_at=m.created_at.isoformat()
            ) for m in messages
        ],
        last_read_at=session.last_read_at.isoformat() if session.last_read_at else None,
        is_new_session=is_new_session
    )

@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limiter)
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
        slug = request.agent_id or "ai_tutor"
        q = q.where(ChatSession.agent_slug == slug).where(ChatSession.schedule_id == None, ChatSession.library_id == None)
        
    result = await db.execute(q)
    chat_session = result.scalar_one_or_none()
    
    if not chat_session:
        # Create new session
        slug = request.agent_id or "ai_tutor"
        
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
        
        # --- DELAYED AUTO GREETING (1 second) ---
        # Send greeting AFTER frontend loads history to trigger notification
        # BUT NOT for ai_tutor (frontend handles it)
        if slug != "ai_tutor":
            async def send_delayed_greeting():
            await asyncio.sleep(1)  # Wait 1 second
            
            # Create new DB session for background task
            async with AsyncSessionLocal() as bg_db:
                agent_res = await bg_db.execute(select(Agent).where(Agent.slug == slug))
                agent_obj = agent_res.scalar_one_or_none()
                agent_name = agent_obj.name if agent_obj else "AI Assistant"
                
                # Priority: 1. DB Greeting, 2. Hardcoded Greeting, 3. Default
                greeting_text = None
                if agent_obj and agent_obj.greeting_message:
                    greeting_text = agent_obj.greeting_message
                
                if not greeting_text:
                    greeting_text = GREETINGS.get(slug, f"Привет! Я {agent_name}. Чем могу помочь?")
                    
                greeting_msg = Message(
                    session_id=chat_session.id,
                    role=MessageRole.ASSISTANT,
                    content=greeting_text
                )
                bg_db.add(greeting_msg)
                
                # Update session timestamps
                session_stmt = select(ChatSession).where(ChatSession.id == chat_session.id)
                session_result = await bg_db.execute(session_stmt)
                session = session_result.scalar_one_or_none()
                if session:
                    session.last_message_at = datetime.utcnow()
                    session.last_read_at = datetime(2000, 1, 1)  # Mark as unread
                
                await bg_db.commit()
                
                # 🔔 Notify User (New Greeting Message)
                await manager.broadcast(current_user.id, {"type": "chatStatusUpdate"})
        
            # Start background task (don't await)
            asyncio.create_task(send_delayed_greeting())
        # ---------------------

    # 3. Save User Message
    # 3. Save User Message
    # We take the LAST message from the client as the new one
    if request.messages and request.save_user_message:
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
        agent_slug = request.agent_id or "ai_tutor"
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
        agent_slug = request.agent_id or "ai_tutor"
        agent_res = await db.execute(select(Agent).where(Agent.slug == agent_slug))
        agent_obj = agent_res.scalar_one_or_none()
        if agent_obj and agent_obj.system_prompt:
            system_prompt = agent_obj.system_prompt

    conversation = [{"role": "system", "content": system_prompt}]
    for m in request.messages:
        conversation.append({"role": m.role, "content": m.content})
        
    # --- Context Management Check ---
    # Получаем настройки чата из БД
    from services.settings_service import get_chat_settings
    chat_settings = await get_chat_settings(db)
    
    current_model = chat_settings.user_chat_model # Используем модель для общения с пользователями
    
    # Проверяем переполнение
    if is_context_overflow(
        conversation, 
        max_tokens=chat_settings.context_soft_limit, 
        threshold=chat_settings.context_threshold, 
        model=current_model
    ):
        background_tasks.add_task(
            compress_context_task, 
            session_id=chat_session.id, 
            keep_last_n=chat_settings.context_compression_keep_last,
            model=chat_settings.compression_model  # Используем модель для сжатия
        )
        
    # 5. Stream & Save
    async def response_generator():
        full_response = ""
        try:
            async for chunk in stream_chat_response(
                conversation, 
                model=chat_settings.user_chat_model,
                temperature=chat_settings.user_chat_temperature,
                max_tokens=chat_settings.user_chat_max_tokens,
                user_id=current_user.id,
                agent_slug=request.agent_id or "ai_tutor"
            ):
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
                     # Use explicit UPDATE to avoid detached instance issues after previous commits
                     await db.execute(
                         update(ChatSession)
                         .where(ChatSession.id == chat_session.id)
                         .values(last_message_at=datetime.utcnow())
                     )
                     
                     await db.commit()
                     
                     # 🔔 Notify User (AI Response Finished)
                     # Trigger global update to refresh lists and bells
                     await manager.broadcast(current_user.id, {"type": "chatStatusUpdate"})
                     
                 except Exception as ex:
                     logger.error(f"❌ Failed to save AI response to database: {ex}", exc_info=True)

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
    
    # 🔔 Notify User (Read Status Changed)
    await manager.broadcast(current_user.id, {"type": "chatStatusUpdate"})
    
    return {"status": "ok", "last_read_at": session.last_read_at.isoformat()}


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
    # We need detailed info for the frontend to decide where to route (agent vs assistant)
    q = select(ChatSession).where(
        ChatSession.user_id == current_user.id,
        ChatSession.is_active == True,
        ChatSession.schedule_id == None,
        ChatSession.library_id == None
    )
    res = await db.execute(q)
    sessions = res.scalars().all()
    
    sessions_data = []
    has_global_unread = False
    
    for session in sessions:
        has_unread = False
        if session.last_message_at:
            if not session.last_read_at:
                has_unread = True
            elif session.last_message_at > session.last_read_at:
                has_unread = True
        
        if has_unread:
            has_global_unread = True
            
        sessions_data.append({
            "agent_slug": session.agent_slug,
            "unread_count": 1 if has_unread else 0
        })
    
    return {
        "has_unread": has_global_unread,
        "sessions": sessions_data
    }




@router.get("/notifications/stream")
async def stream_notifications(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    SSE Endpoint for real-time notifications.
    Client connects here and hangs waiting for events.
    """
    queue = await manager.connect(current_user.id)
    
    async def event_generator():
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                    
                # Wait for data with timeout to send keepalive
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield data
                except asyncio.TimeoutError:
                    # Keep-alive (comment character for SSE)
                    yield ": keepalive\n\n"
                    
        except Exception as e:
            print(f"SSE Stream Error: {e}")
        finally:
            manager.disconnect(current_user.id, queue)
            
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

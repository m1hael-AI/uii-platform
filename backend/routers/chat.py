from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, or_, update, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import asyncio
import json
import logging
import yaml
from pathlib import Path

from services.openai_service import generate_chat_response, stream_chat_response
from services.context_manager import is_context_overflow, compress_context_task
from dependencies import get_db, get_current_user, rate_limiter
from models import User, ChatSession, Message, MessageRole, Agent, PendingAction, WebinarLibrary, WebinarSchedule, UserMemory
from config import settings
from loguru import logger
from services.chat_session_service import get_or_create_chat_session

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
    
    # Context Awareness
    page_context: Optional[Dict[str, Any]] = None # {url, title, element_id, ...}

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

class AgentDTO(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    greeting_message: Optional[str] = None

@router.get("/agents", response_model=List[AgentDTO])
async def get_available_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of all available AI agents"""
    # Exclude main_assistant if it's treated specially as a "system" agent, 
    # but for now let's return everything and let frontend filter if needed.
    # Actually, main_assistant is usually the "Help" bot, not in the specialist list.
    # But let's return all ACTIVE agents.
    
    result = await db.execute(
        select(Agent)
        .where(Agent.is_active == True)
        .order_by(Agent.id) # Or explicit order
    )
    agents = result.scalars().all()
    
    return [
        AgentDTO(
            id=a.id,
            slug=a.slug,
            name=a.name,
            description=a.description,
            avatar_url=a.avatar_url,
            greeting_message=a.greeting_message
        ) for a in agents if a.slug not in ["main_assistant", "ai_tutor"] # Exclude system agents
    ]

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
        
    # 2. Setup initial sessions for ALL active agents + main_assistant
    # Fetch all active agents
    agents_res = await db.execute(select(Agent).where(Agent.is_active == True))
    agents = agents_res.scalars().all()
    
    # We want sessions for main_assistant + all other agents
    target_slugs = set([a.slug for a in agents])
    if "main_assistant" not in target_slugs:
        # Should not happen if seeded correctly, but just in case
        pass 

    for agent in agents:
        slug = agent.slug
        if slug == "ai_tutor": continue # Skip specialized agents if needed (e.g. tutor)

        try:
            # Use atomic get_or_create
            session_result = await get_or_create_chat_session(db, user_id, slug)
            new_session = session_result
            # Check if we just created it? get_or_create doesn't return created bool usually
            # But we check `if res.first(): return False` at the top, so we assume these are new 
            # OR we check if messages exist.
            
            # Actually, get_or_create might return existing. 
            # We want to send greeting ONLY if no messages exist.
            
            # Check for messages
            msg_check = await db.execute(select(Message).where(Message.session_id == new_session.id))
            if msg_check.first():
                continue # Already has messages
            
            # Create greeting
            if slug != "main_assistant":
                welcome_text = agent.greeting_message or "Привет! Чем могу помочь?"
                
                msg = Message(
                    session_id=new_session.id,
                    role=MessageRole.ASSISTANT,
                    content=welcome_text,
                    created_at=datetime.utcnow()
                )
                db.add(msg)
                
                # Update session timestamps
                new_session.last_message = welcome_text # Ensure preview works!
                new_session.last_message_at = datetime.utcnow()
                # Mark as UNREAD by setting last_read_at to old date
                new_session.last_read_at = datetime(2000, 1, 1) 
                
        except Exception as e:
            logger.error(f"Error creating initial session for {slug}: {e}")
            continue
    
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
            # Force unread if last_read_at is the "magic" cold start date (year 2000)
            if session.last_read_at and session.last_read_at.year < 2001:
                has_unread = True
            elif not session.last_read_at:
                has_unread = True
            elif session.last_message_at > session.last_read_at:
                has_unread = True
        
        # DEBUG LOG for startup_expert to trace unread logic
        if agent.slug == 'startup_expert':
             print(f"👉 [BACKEND] GET_SESSIONS 'startup_expert': LastMsg={session.last_message_at}, LastRead={session.last_read_at}, Unread={has_unread}")

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
    sessions = result.scalars().all()
    
    # Handle race condition: if multiple sessions exist, use the first one
    if len(sessions) > 1:
        logger.warning(f"Multiple sessions found for user {current_user.id}, agent {agent_id}. Using first one.")
        session = sessions[0]
    elif len(sessions) == 1:
        session = sessions[0]
    else:
        session = None
    
        # ✅ 1. Auto-create session if it doesn't exist (Lazy Load)
        # This ensures we have a place to put the greeting immediately
        session = await get_or_create_chat_session(
            db=db,
            user_id=current_user.id,
            agent_slug=agent_id,
            webinar_id=webinar_id
        )
        
        
        # ✅ 2. Create Synchronous Greeting
        # Get greeting text
        if agent_id == "main_assistant":
            greeting_text = "Здравствуйте! Я ваш AI-помощник. Я всегда под рукой в боковой панели, чтобы помочь с любым вопросом. С чего начнем?"
        else:
             # Look up agent name if needed
            agent_name = "AI Assistant"
            if agent_id == "ai_tutor":
                agent_name = "AI Тьютор"
            else:
                 agent_res = await db.execute(select(Agent).where(Agent.slug == agent_id))
                 agent_obj = agent_res.scalar_one_or_none()
                 if agent_obj: agent_name = agent_obj.name

            greeting_text = GREETINGS.get(agent_id, f"Привет! Я {agent_name}. Чем могу помочь?")
            
        greeting_msg = Message(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=greeting_text,
            created_at=datetime.utcnow()
        )
        db.add(greeting_msg)
        await db.commit()
        await db.refresh(session)
        
        # Return newly created history directly
        return HistoryResponse(
            messages=[
                HistoryMessage(
                    role=greeting_msg.role.value,
                    content=greeting_msg.content,
                    created_at=greeting_msg.created_at.isoformat()
                )
            ],
            last_read_at=session.last_read_at.isoformat() if session.last_read_at else None,
            is_new_session=True
        )
        
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
    
    # If session exists but has NO messages (e.g. manually cleared), trigger sync greeting
    # CRITICAL: Check all_messages (total history), not just filters, to avoid duplicates on refresh
    if len(all_messages) == 0 and agent_id:
         # Same logic as above but for existing session
        if agent_id == "main_assistant":
            greeting_text = "Здравствуйте! Я ваш AI-помощник. Я всегда под рукой в боковой панели, чтобы помочь с любым вопросом. С чего начнем?"
        else:
            agent_name = "AI Assistant" # Fallback
            if agent_id == "ai_tutor":
                agent_name = "AI Тьютор"
            else:
                 # Look up agent name if needed
                 agent_res = await db.execute(select(Agent).where(Agent.slug == agent_id))
                 agent_obj = agent_res.scalar_one_or_none()
                 if agent_obj: agent_name = agent_obj.name
            
            greeting_text = GREETINGS.get(agent_id, f"Привет! Я {agent_name}. Чем могу помочь?")
            
        greeting_msg = Message(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=greeting_text,
            created_at=datetime.utcnow()
        )
        db.add(greeting_msg)
        await db.commit()
        
        # Add to messages list to return immediately
        messages.append(greeting_msg)
    
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

from services.rag_service import search_relevant_chunks, format_rag_context

@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limiter)
):
    # 0. Extract Last User Message (Early)
    last_user_msg_content = ""
    if request.messages:
        last_user_msg_content = request.messages[-1].content

    # 1. Get Webinar Context (RAG vs Full)
    webinar_context = ""
    if request.webinar_id:
        # A. Try RAG Search first (Optimization)
        # We only want to fallback if RAG *cannot* be used (i.e. webinar not indexed yet).
        # If webinar IS indexed but returns no chunks (irrelevant query), we should NOT dump pure transcript.
        
        # 1. Search
        chunks = []
        if last_user_msg_content:
            chunks = await search_relevant_chunks(db, last_user_msg_content, webinar_id=request.webinar_id)
            
        if chunks:
            webinar_context = await format_rag_context(chunks)
            logger.info(f"🔍 RAG found {len(chunks)} chunks for query: '{last_user_msg_content[:20]}...'")
        else:
            # 2. Check if webinar is indexed at all
            # If it has chunks, but search returned nothing -> Query is irrelevant. Do NOT fallback.
            # If it has NO chunks -> It's a legacy/unprocessed webinar. Fallback to full transcript.
            
            # Simple existence check (limit 1 is enough)
            from sqlalchemy import exists
            # We can't easily import `WebinarChunk` here without circular imports if not careful, 
            # but it is imported in `models`.
            # Let's use a quick scalar query.
            from models import WebinarChunk
            
            has_chunks = await db.scalar(
                select(func.count(WebinarChunk.id)).where(WebinarChunk.webinar_id == request.webinar_id)
            )
            
            if has_chunks and has_chunks > 0:
                 logger.info(f"🚫 RAG found nothing (relevant), but webinar is indexed. Skipping fallback.")
                 # Context remains empty - this is correct for irrelevant queries.
            else:
                # B. Fallback to Full Transcript (Legacy/Short webinars)
                # Try retrieving context from WebinarLibrary
                res = await db.execute(select(WebinarLibrary).where(WebinarLibrary.id == request.webinar_id))
                w = res.scalar_one_or_none()
                if w and w.transcript_context:
                    webinar_context = w.transcript_context
                    logger.info(f"📜 RAG empty & Not Indexed, using full transcript ({len(webinar_context)} chars)")
                else:
                    # Fallback (rare): try Schedule
                    res_sch = await db.execute(select(WebinarSchedule).where(WebinarSchedule.id == request.webinar_id))
                    w_sch = res_sch.scalar_one_or_none()
                    if w_sch and hasattr(w_sch, 'transcript_context') and w_sch.transcript_context:
                         webinar_context = w_sch.transcript_context

    # 2. Get or Create Session
    chat_session = await get_or_create_chat_session(
        db=db,
        user_id=current_user.id,
        agent_slug=request.agent_id or "ai_tutor",
        webinar_id=request.webinar_id
    )
        
        # No delayed greeting here. Greeting is handled by get_chat_history or created synchronously if needed.

    # 3. Save User Message
    # We take the LAST message from the client as the new one
    if request.messages and request.save_user_message:
        # last_user_msg_content already extracted at step 0
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
        
        # Check how many pending tasks exist before deletion
        pending_count = await db.scalar(
            select(func.count(PendingAction.id))
            .where(PendingAction.user_id == current_user.id)
            .where(PendingAction.agent_slug == agent_slug)
            .where(PendingAction.status == "pending")
        )
        
        if pending_count and pending_count > 0:
            logger.info(f"🔪 Kill Switch: Deleting {pending_count} pending task(s) for user={current_user.id}, agent={agent_slug}")
        
        result = await db.execute(
            delete(PendingAction)
            .where(PendingAction.user_id == current_user.id)
            .where(PendingAction.agent_slug == agent_slug)
            .where(PendingAction.status == "pending")
        )
        
        await db.commit()
        
        # Log successful deletion
        if pending_count and pending_count > 0:
            logger.info(f"✅ Kill Switch: Successfully deleted {pending_count} pending task(s)")

    # 4. Building Context (Memory v2)
    # =========================================================================
    # A. Fetch History from DB (Active only)
    # We ignore frontend 'messages' list for context building. We trust the DB.
    # This automatically includes [SUMMARY] messages (role=SYSTEM) from compression.
    
    # Load all non-archived messages (rely on context compression for token management)
    # Context overflow check will trigger compression if needed
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == chat_session.id)
        .where(Message.is_archived == False)
        .order_by(Message.created_at.desc()) # Fetch latest first
    )
    # Reverse to restore chronological order (Oldest -> Newest)
    history_messages = list(reversed(history_result.scalars().all()))
    
    # B. Fetch Memory (for Injection)
    # 1. Global Profile (UserMemory)
    user_memory_res = await db.execute(select(UserMemory).where(UserMemory.user_id == current_user.id))
    user_memory = user_memory_res.scalar_one_or_none()
    global_profile = user_memory.narrative_summary if user_memory and user_memory.narrative_summary else "Неизвестно"
    
    # 2. Local Profile (User-Agent Profile)
    # Previously 'local_summary'. Now 'user_agent_profile'.
    local_profile = chat_session.user_agent_profile if chat_session.user_agent_profile else "Неизвестно"

    # C. Prepare System Prompt
    system_prompt = "You are a helpful AI Assistant."
    
    # C. Prepare System Prompt (Unified Logic)
    # Always load from DB first
    agent_slug = request.agent_id or "ai_tutor"
    agent_res = await db.execute(select(Agent).where(Agent.slug == agent_slug))
    agent_obj = agent_res.scalar_one_or_none()
    
    if agent_obj and agent_obj.system_prompt:
        system_prompt = agent_obj.system_prompt
    else:
        system_prompt = "You are a helpful AI Assistant." # Fallback

    # D. INJECTION
    
    # Context Awareness Injection removed to isolate RAG testing
    
    # 1. Webinar Context Injection
    
    # D. INJECTION
    
    # 1. Memory Injection (FIRST)
    # We rely on specific placeholders in the prompt text: {user_profile}, {user_agent_profile}
    system_prompt = system_prompt.replace("{user_profile}", global_profile)
    system_prompt = system_prompt.replace("{user_agent_profile}", local_profile)
    system_prompt = system_prompt.replace("{local_summary}", local_profile) # Legacy support

    # 2. Webinar Context Injection (SECOND - Dynamic Size)
    if webinar_context:
        from config import settings # Lazy import
        from services.context_manager import get_model_limit
        from utils.token_counter import count_string_tokens_async, count_tokens_from_messages_async, get_encoding
        
        model_name = settings.openai_model
        max_model_tokens = get_model_limit(model_name)
        
        # Calculate Used Tokens
        # A. System Prompt (so far)
        system_prompt_tokens = await count_string_tokens_async(system_prompt, model=model_name)
        
        # B. Response Buffer (Reserve space for answer)
        RESPONSE_BUFFER = 4000 # Safe default for long answers
        
        # C. Webinar Context (Measure First - PRIORITY)
        context_tokens = await count_string_tokens_async(webinar_context, model=model_name)
        
        # D. Calculate Space for History
        # Limit - (System + Webinar + Buffer)
        reserved_tokens = system_prompt_tokens + context_tokens + RESPONSE_BUFFER
        available_for_history = max_model_tokens - reserved_tokens
        
        safe_context = webinar_context
        
        if available_for_history < 0:
            # CRITICAL: Webinar + System > Model Limit. 
            # We MUST truncate the webinar context as a last resort, otherwise the request fails.
            available_context_tokens = max(1000, max_model_tokens - system_prompt_tokens - RESPONSE_BUFFER)
            logger.error(f"🚨 CRITICAL: Webinar context ({context_tokens}) + System ({system_prompt_tokens}) exceeds model limit ({max_model_tokens})! Truncating webinar to {available_context_tokens} tokens.")
            
            # Smart Truncation via tiktoken
            encoding = get_encoding(model_name)
            encoded = encoding.encode(webinar_context)
            truncated_encoded = encoded[:available_context_tokens]
            safe_context = encoding.decode(truncated_encoded)
            
            # No space for history
            history_messages = [] 
            logger.warning("⚠️ Dropping ALL history to fit truncated webinar context.")
            
        else:
            # We have space for history?
            # Convert history_messages (DB objects) to dicts for counting
            history_dicts = [{"role": m.role.value, "content": m.content} for m in history_messages]
            history_tokens = await count_tokens_from_messages_async(history_dicts, model=model_name)
            
            if history_tokens > available_for_history:
                 logger.warning(f"⚠️ History too large ({history_tokens} tokens) for remaining space ({available_for_history}). Trimming history for this request.")
                 
                 # Optimized trim logic: iterate from end and add until full
                 trimmed_history = []
                 current_tokens = 0
                 # Reverse iteration (newest first)
                 for msg in reversed(history_messages):
                     # Estimate tokens for one message (approximate overhead 4 tokens)
                     # Calling async counter for every message is slow, but safe
                     msg_dict = {"role": msg.role.value, "content": msg.content}
                     msg_tokens = await count_tokens_from_messages_async([msg_dict], model=model_name)
                     
                     if current_tokens + msg_tokens > available_for_history:
                         break
                     
                     trimmed_history.insert(0, msg)
                     current_tokens += msg_tokens
                 
                 history_messages = trimmed_history

        formatted_context = (
            f"\n=== КОНТЕКСТ ВЕБИНАРА (ТРАНСКРИПЦИЯ) ===\n"
            f"Используй ТОЛЬКО следующий текст для ответов на вопросы пользователя:\n"
            f"--- НАЧАЛО ТЕКСТА ---\n"
            f"{safe_context}\n"
            f"--- КОНЕЦ ТЕКСТА ---\n"
            f"==========================================\n"
        )
        
        # Inject into placeholder
        if "{webinar_context}" in system_prompt:
            system_prompt = system_prompt.replace("{webinar_context}", formatted_context)
        else:
            # If agent doesn't have placeholder but context exists -> that's weird but not fatal.
            pass
            
    else:
        # NO CONTEXT PROVIDED
        # Check if it was supposed to be AI Tutor?
        if agent_slug == "ai_tutor":
            logger.error(f"🚨 AI Tutor invoked without webinar_context! Agent will be blind.")
            
        # Clean up placeholder
        system_prompt = system_prompt.replace("{webinar_context}", "")

    # E. Construct Conversation
    conversation = [{"role": "system", "content": system_prompt}]
    
    for m in history_messages:
        conversation.append({"role": m.role.value, "content": m.content})
        
    # --- Context Management Check ---
    # Получаем настройки чата из БД
    from services.settings_service import get_chat_settings
    chat_settings = await get_chat_settings(db)
    
    current_model = chat_settings.user_chat_model # Используем модель для общения с пользователями
    
    # Проверяем переполнение
    if await is_context_overflow(
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
                     now_utc = datetime.utcnow()
                     await db.execute(
                         update(ChatSession)
                         .where(ChatSession.id == chat_session.id)
                         .values(last_message_at=now_utc)
                     )
                     
                     await db.commit()
                     print(f"👉 [BACKEND] MSG_SAVED. Session={chat_session.id}, Agent={agent_slug}, MsgTime={now_utc}")
                     
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
    request: Request,
    webinar_id: Optional[int] = None,
    agent_id: Optional[str] = "mentor",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark chat session as read (update last_read_at)"""
    # DEBUG LOG
    source = request.headers.get("X-Caller-Source", "Unknown")
    print(f"👉 [BACKEND] MARK_READ. Agent={agent_id}, User={current_user.id}, Source={source}, Time={datetime.utcnow()}")
    
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
    # 🔔 Notify User (Read Status Changed)
    # FIX: Use specific event 'chatReadUpdate' instead of generic 'chatStatusUpdate' 
    # to avoid infinite loop (Frontend reloads history on statusUpdate -> calls read -> triggers statusUpdate)
    await manager.broadcast(current_user.id, {"type": "chatReadUpdate"})
    
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
    # FIX: Ensure current_user is attached to current session to avoid MissingGreenlet
    # if the object is detached/expired from the dependency session.
    # However, merge returns a NEW instance.
    if current_user not in db:
       current_user = await db.merge(current_user)

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

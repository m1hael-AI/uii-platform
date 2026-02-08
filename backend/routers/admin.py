from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from dependencies import get_db, get_current_user
from models import User, UserRole, Agent, ProactivitySettings, ChatSettings

router = APIRouter(prefix="/admin", tags=["admin"])

# --- Models ---

class AgentUpdate(BaseModel):
    system_prompt: str
    description: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    greeting_message: Optional[str] = None
    avatar_url: Optional[str] = None

class AgentResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str]
    system_prompt: str
    is_active: bool
    greeting_message: Optional[str] = None
    avatar_url: Optional[str] = None




class ProactivitySettingsUpdate(BaseModel):
    # Memory Update Settings
    memory_model: Optional[str] = None
    memory_temperature: Optional[float] = None
    memory_max_tokens: Optional[int] = None
    
    # Proactivity Trigger Settings
    trigger_model: Optional[str] = None
    trigger_temperature: Optional[float] = None
    trigger_max_tokens: Optional[int] = None
    
    # Scheduler Settings
    enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    
    # Limits
    max_messages_per_day_agents: Optional[int] = None
    max_messages_per_day_assistant: Optional[int] = None

    # Rate Limiter
    rate_limit_per_minute: Optional[int] = None
    
    # Summarizer Settings
    summarizer_check_interval: Optional[int] = None
    summarizer_idle_threshold: Optional[int] = None

    # Context Compression
    context_soft_limit: Optional[int] = None
    context_threshold: Optional[float] = None
    context_compression_keep_last: Optional[int] = None
    
    # Prompts
    agent_memory_prompt: Optional[str] = None
    assistant_memory_prompt: Optional[str] = None
    proactivity_trigger_prompt: Optional[str] = None
    compression_prompt: Optional[str] = None
    
    # Architecture v2 Timings
    memory_update_interval: Optional[float] = None
    proactivity_timeout: Optional[float] = None
    
    # Anti-Spam
    max_consecutive_messages: Optional[int] = None

class ProactivitySettingsResponse(BaseModel):
    id: int
    # Memory Update Settings
    memory_model: str
    memory_temperature: float
    memory_max_tokens: Optional[int]
    
    # Proactivity Trigger Settings
    trigger_model: str
    trigger_temperature: float
    trigger_max_tokens: Optional[int]
    
    # Scheduler Settings
    enabled: bool
    cron_expression: str
    quiet_hours_start: str
    quiet_hours_end: str
    
    # Limits
    max_messages_per_day_agents: int
    max_messages_per_day_assistant: int

    # Rate Limiter
    rate_limit_per_minute: int
    
    # Summarizer Settings
    summarizer_check_interval: int
    summarizer_idle_threshold: int

    # Context Compression
    context_soft_limit: Optional[int] = None
    context_threshold: Optional[float] = None
    context_compression_keep_last: Optional[int] = None
    
    # Prompts
    agent_memory_prompt: str
    assistant_memory_prompt: str
    proactivity_trigger_prompt: str
    compression_prompt: str
    
    # Architecture v2 Timings
    memory_update_interval: float
    proactivity_timeout: float
    
    # Anti-Spam
    max_consecutive_messages: int


# === Chat Settings Models ===

class ChatSettingsUpdate(BaseModel):
    # Блок 1: Общение с пользователями
    user_chat_model: Optional[str] = None
    user_chat_temperature: Optional[float] = None
    user_chat_max_tokens: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    
    # Блок 2: Вечный диалог (Сжатие контекста)
    compression_model: Optional[str] = None
    compression_temperature: Optional[float] = None
    compression_max_tokens: Optional[int] = None
    context_threshold: Optional[float] = None
    context_compression_keep_last: Optional[int] = None
    context_soft_limit: Optional[int] = None
    
    # Aggregated from Proactivity (UI convenience)
    compression_prompt: Optional[str] = None


class ChatSettingsResponse(BaseModel):
    id: int
    # Блок 1: Общение с пользователями
    user_chat_model: str
    user_chat_temperature: float
    user_chat_max_tokens: Optional[int]
    rate_limit_per_minute: int
    
    # Блок 2: Вечный диалог (Сжатие контекста)
    compression_model: str
    compression_temperature: float
    compression_max_tokens: Optional[int]
    context_threshold: float
    context_compression_keep_last: int
    context_soft_limit: int
    
    # Aggregated from Proactivity (UI convenience)
    compression_prompt: str
    
    updated_at: datetime

# --- Helpers ---

def verify_admin(user: User):
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin privileges required"
        )

# --- Endpoints ---

@router.get("/agents", response_model=List[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all agents (Admin only)"""
    verify_admin(current_user)
    
    result = await db.execute(select(Agent).order_by(Agent.id))
    agents = result.scalars().all()
    return agents

@router.patch("/agents/{slug}", response_model=AgentResponse)
async def update_agent(
    slug: str,
    update_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update agent prompt or settings (Admin only)"""
    verify_admin(current_user)
    
    result = await db.execute(select(Agent).where(Agent.slug == slug))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if update_data.system_prompt is not None:
        agent.system_prompt = update_data.system_prompt
    if update_data.description is not None:
        agent.description = update_data.description
    if update_data.name is not None:
        agent.name = update_data.name
    if update_data.is_active is not None:
        agent.is_active = update_data.is_active
    if update_data.greeting_message is not None:
        agent.greeting_message = update_data.greeting_message
    if update_data.avatar_url is not None:
        agent.avatar_url = update_data.avatar_url
        
    await db.commit()
    await db.refresh(agent)
    return agent

# --- Proactivity Settings ---

@router.get("/proactivity", response_model=ProactivitySettingsResponse)
async def get_proactivity_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get proactivity settings (Admin only)"""
    verify_admin(current_user)
    
    result = await db.execute(select(ProactivitySettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Create default settings if not exist
        settings = ProactivitySettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings

@router.patch("/proactivity", response_model=ProactivitySettingsResponse)
async def update_proactivity_settings(
    update_data: ProactivitySettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update proactivity settings (Admin only)"""
    verify_admin(current_user)
    
    result = await db.execute(select(ProactivitySettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = ProactivitySettings()
        db.add(settings)
    
    
    # Use Pydantic's exclude_unset to only update fields that were explicitly provided
    # This allows setting fields to None (NULL) when the user clears them
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(settings, field, value)
    
    # Update timestamp
    from datetime import datetime
    settings.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(settings)
    return settings


# === Chat Settings Endpoints ===

@router.get("/chat-settings", response_model=ChatSettingsResponse)
async def get_chat_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat settings (Admin only)"""
    verify_admin(current_user)
    
    result = await db.execute(select(ChatSettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Create default settings if not exist
        settings = ChatSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    # Fetch compression_prompt from ProactivitySettings
    proactivity_result = await db.execute(select(ProactivitySettings))
    proactivity = proactivity_result.scalar_one_or_none()
    
    compression_prompt_value = ""
    if proactivity:
        compression_prompt_value = proactivity.compression_prompt
    else:
        # Should ideally exist or be created, but for safety providing default
        # If proactivity settings are missing, we might want to create them or just use empty string
        compression_prompt_value = ProactivitySettings().compression_prompt

    # Merge into response
    # We construct the response manually or simply attach the attribute if Pydantic model allows it
    # Pydantic models are strict, so we construct a dict or object that satisfies ChatSettingsResponse
    
    response_data = settings.dict() if hasattr(settings, 'dict') else {c.name: getattr(settings, c.name) for c in settings.__table__.columns}
    response_data['compression_prompt'] = compression_prompt_value
    
    return response_data


@router.patch("/chat-settings", response_model=ChatSettingsResponse)
async def update_chat_settings(
    update_data: ChatSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update chat settings (Admin only)"""
    verify_admin(current_user)
    
    result = await db.execute(select(ChatSettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = ChatSettings()
        db.add(settings)
    
    
    # Use Pydantic's exclude_unset to only update fields that were explicitly provided
    # This allows setting fields to None (NULL) when the user clears them
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Handle compression_prompt separately (it's stored in ProactivitySettings)
    compression_prompt_update = update_dict.pop('compression_prompt', None)
    
    # Update ChatSettings fields
    for field, value in update_dict.items():
        setattr(settings, field, value)
    
    # Update timestamp
    settings.updated_at = datetime.utcnow()
    
    # Update compression_prompt in ProactivitySettings if provided
    if 'compression_prompt' in update_data.model_dump(exclude_unset=True):
        proactivity_result = await db.execute(select(ProactivitySettings))
        proactivity = proactivity_result.scalar_one_or_none()
        
        if not proactivity:
            proactivity = ProactivitySettings()
            db.add(proactivity)
            
        proactivity.compression_prompt = update_data.compression_prompt
        # Ensure we commit proactivity changes too
        # They are in the same session, so one commit is enough
    
    await db.commit()
    await db.refresh(settings)
    
    # Re-fetch proactivity prompt for response
    proactivity_result = await db.execute(select(ProactivitySettings))
    proactivity = proactivity_result.scalar_one_or_none()
    promt_val = proactivity.compression_prompt if proactivity else ""
    
    response_data = settings.dict() if hasattr(settings, 'dict') else {c.name: getattr(settings, c.name) for c in settings.__table__.columns}
    response_data['compression_prompt'] = promt_val
    
    return response_data

# --- Users Management ---

class AdminUserResponse(BaseModel):
    id: int
    tg_id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = Field(default=None, validation_alias="tg_username")
    role: str
    tg_first_name: Optional[str] = None
    tg_last_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.get("/users", response_model=List[AdminUserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users (Admin only)"""
    verify_admin(current_user)
    
    result = await db.execute(select(User).order_by(User.id.desc()))
    users = result.scalars().all()
    
    # Return as is, Pydantic will filter fields based on AdminUserResponse
    return users


# --- System Config (Key-Value) ---

from models import SystemConfig

class SystemConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None

@router.get("/configs", response_model=List[SystemConfig])
async def list_system_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all system configs"""
    verify_admin(current_user)
    result = await db.execute(select(SystemConfig))
    return result.scalars().all()

@router.put("/configs/{key}", response_model=SystemConfig)
async def update_system_config(
    key: str,
    config: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update or Create a System Configuration Key"""
    verify_admin(current_user)
    
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.value = config.value
        if config.description:
            existing.description = config.description
        existing.updated_at = datetime.utcnow()
    else:
        existing = SystemConfig(
            key=key,
            value=config.value,
            description=config.description
        )
        db.add(existing)
        
    await db.commit()
    await db.refresh(existing)
    return existing

@router.get("/users", response_model=List[AdminUserResponse])
async def list_users(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users with optional search by username"""
    verify_admin(current_user)
    
    stmt = select(User)
    
    if q:
        stmt = stmt.where(User.tg_username.ilike(f"%{q}%"))
        
    stmt = stmt.order_by(User.created_at.desc()).limit(50)
    
    result = await db.execute(stmt)
    return result.scalars().all()


# --- LLM Audit Logs ---

from models import LLMAudit
from sqlalchemy import func

class LLMAuditResponse(BaseModel):
    id: int
    user_id: int
    agent_slug: str
    model: str
    
    # Stats
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: int
    
    # Content (Full Log)
    request_json: str
    response_json: str
    
    # Metadata
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class LLMAuditListResponse(BaseModel):
    items: List[LLMAuditResponse]
    total: int
    page: int
    limit: int

@router.get("/llm-audit", response_model=LLMAuditListResponse)
async def list_llm_audit_logs(
    page: int = 1,
    limit: int = 20,
    user_id: Optional[int] = None,
    agent_slug: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List LLM Audit Logs with pagination and filtering (Admin only)"""
    verify_admin(current_user)
    
    offset = (page - 1) * limit
    
    # Base query
    stmt = select(LLMAudit)
    count_stmt = select(func.count()).select_from(LLMAudit)
    
    # Apply filters
    if user_id:
        stmt = stmt.where(LLMAudit.user_id == user_id)
        count_stmt = count_stmt.where(LLMAudit.user_id == user_id)
    
    if agent_slug:
        stmt = stmt.where(LLMAudit.agent_slug.ilike(f"%{agent_slug}%"))
        count_stmt = count_stmt.where(LLMAudit.agent_slug.ilike(f"%{agent_slug}%"))
        
    if status:
        stmt = stmt.where(LLMAudit.status == status)
        count_stmt = count_stmt.where(LLMAudit.status == status)
        
    # Order by newest first
    stmt = stmt.order_by(LLMAudit.created_at.desc())
    
    # Pagination
    stmt = stmt.offset(offset).limit(limit)
    
    # Execute
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return LLMAuditListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit
    )

# --- Clear User Data (For Testing) ---

@router.delete("/users/{user_id}/data")
async def clear_user_data(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    🗑️ DANGER: Clear ALL data for a specific user.
    Only for ADMIN. Used for testing purposes.
    
    Deletes:
    - Messages
    - Chat Sessions
    - User Memory
    - Pending Actions
    - LLM Audit Logs
    """
    # CRITICAL: Only admin can clear user data
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can clear user data"
        )
    
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    from models import Message, ChatSession, UserMemory, PendingAction, LLMAuditLog
    from sqlalchemy import delete
    
    # 1. Delete Messages
    await db.execute(
        delete(Message).where(
            Message.session_id.in_(
                select(ChatSession.id).where(ChatSession.user_id == user_id)
            )
        )
    )
    
    # 2. Delete Chat Sessions
    await db.execute(delete(ChatSession).where(ChatSession.user_id == user_id))
    
    # 3. Delete User Memory
    await db.execute(delete(UserMemory).where(UserMemory.user_id == user_id))
    
    # 4. Delete Pending Actions
    await db.execute(delete(PendingAction).where(PendingAction.user_id == user_id))
    
    # 5. Delete LLM Audit Logs
    await db.execute(delete(LLMAuditLog).where(LLMAuditLog.user_id == user_id))
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"All data for user {user_id} ({user.username or user.tg_first_name}) has been cleared",
        "user_id": user_id
    }

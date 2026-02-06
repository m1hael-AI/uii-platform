from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from dependencies import get_db, get_current_user
from models import User, UserRole, Agent, ProactivitySettings

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
    # OpenAI Settings
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    # Scheduler Settings
    enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    
    # Limits
    max_messages_per_day_agents: Optional[int] = None
    max_messages_per_day_assistant: Optional[int] = None
    
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

class ProactivitySettingsResponse(BaseModel):
    id: int
    # OpenAI Settings
    model: str
    temperature: float
    max_tokens: int
    
    # Scheduler Settings
    enabled: bool
    cron_expression: str
    quiet_hours_start: str
    quiet_hours_end: str
    
    # Limits
    max_messages_per_day_agents: int
    max_messages_per_day_assistant: int
    
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
    
    # Update OpenAI settings
    if update_data.model is not None:
        settings.model = update_data.model
    if update_data.temperature is not None:
        settings.temperature = update_data.temperature
    if update_data.max_tokens is not None:
        settings.max_tokens = update_data.max_tokens
    
    # Update Scheduler settings
    if update_data.enabled is not None:
        settings.enabled = update_data.enabled
    if update_data.cron_expression is not None:
        settings.cron_expression = update_data.cron_expression
    if update_data.quiet_hours_start is not None:
        settings.quiet_hours_start = update_data.quiet_hours_start
    if update_data.quiet_hours_end is not None:
        settings.quiet_hours_end = update_data.quiet_hours_end
    
    # Update Limits
    if update_data.max_messages_per_day_agents is not None:
        settings.max_messages_per_day_agents = update_data.max_messages_per_day_agents
    if update_data.max_messages_per_day_assistant is not None:
        settings.max_messages_per_day_assistant = update_data.max_messages_per_day_assistant
    
    # Update Summarizer settings
    if update_data.summarizer_check_interval is not None:
        settings.summarizer_check_interval = update_data.summarizer_check_interval
    if update_data.summarizer_idle_threshold is not None:
        settings.summarizer_idle_threshold = update_data.summarizer_idle_threshold
    
    # Update Context Compression
    if update_data.context_soft_limit is not None:
        settings.context_soft_limit = update_data.context_soft_limit
    if update_data.context_threshold is not None:
        settings.context_threshold = update_data.context_threshold
    if update_data.context_compression_keep_last is not None:
        settings.context_compression_keep_last = update_data.context_compression_keep_last
    
    # Update Prompts
    if update_data.agent_memory_prompt is not None:
        settings.agent_memory_prompt = update_data.agent_memory_prompt
    if update_data.assistant_memory_prompt is not None:
        settings.assistant_memory_prompt = update_data.assistant_memory_prompt
    
    # Update timestamp
    from datetime import datetime
    settings.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(settings)
    return settings

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


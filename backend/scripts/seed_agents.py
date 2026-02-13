
import asyncio
import os
import sys
import yaml
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from loguru import logger

# Add parent directory to path to import models and config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models import Agent
from database import async_engine

load_dotenv()

async def seed_agents():
    logger.info("🚀 Seeding Agents from default_prompts.yaml...")
    
    # Load YAML
    yaml_path = os.path.join(os.path.dirname(__file__), '../resources/default_prompts.yaml')
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    agents_data = data.get('agents', {})
    if not agents_data:
        logger.warning("❌ No agents found in YAML!")
        return

    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # 1. Deactivate ALL existing agents first (to safely replace roster)
        # We don't delete to preserve chat history, just set is_active=False
        # Except main_assistant and ai_tutor if they exist in new list (we just update them)
        logger.info("💤 Deactivating old agents...")
        
        # Get list of new slugs
        new_slugs = list(agents_data.keys())
        
        # Deactivate agents NOT in the new list
        # Actually, let's just update valid ones and deactivate others.
        
        existing_agents_result = await session.execute(select(Agent))
        existing_agents = existing_agents_result.scalars().all()
        
        for existing in existing_agents:
            if existing.slug not in new_slugs:
                existing.is_active = False
                logger.info(f"   -> Deactivated: {existing.slug}")
            # If it IS in new_slugs, we will update it below.
            
        # 2. Upsert (Update or Insert) new agents
        for slug, info in agents_data.items():
            result = await session.execute(select(Agent).where(Agent.slug == slug))
            agent = result.scalar_one_or_none()
            
            if agent:
                logger.info(f"🔄 Updating agent: {slug}")
                agent.name = info['name']
                agent.description = info['description']
                agent.system_prompt = info['system_prompt']
                agent.greeting_message = info['greeting']
                agent.avatar_url = info['avatar_url']
                agent.is_active = True # Ensure active
            else:
                logger.info(f"✨ Creating new agent: {slug}")
                agent = Agent(
                    slug=slug,
                    name=info['name'],
                    description=info['description'],
                    system_prompt=info['system_prompt'],
                    greeting_message=info['greeting'],
                    avatar_url=info['avatar_url'],
                    is_active=True
                )
                session.add(agent)
        
        await session.commit()
        logger.info("✅ Agents seeding complete!")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_agents())

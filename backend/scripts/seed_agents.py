
import asyncio
import os
import sys
import yaml
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from loguru import logger

# Add parent directory to path to import models and config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models import Agent, ChatSession
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
        # 1. DELETE obsolete agents (and their sessions)
        logger.info("🧹 Cleaning up old agents...")
        
        # Get list of new slugs
        new_slugs = list(agents_data.keys())
        
        existing_agents_result = await session.execute(select(Agent))
        existing_agents = existing_agents_result.scalars().all()
        
        for existing in existing_agents:
            if existing.slug not in new_slugs:
                # Delete sessions first (manual cascade)
                logger.info(f"   -> Deleting sessions for: {existing.slug}")
                await session.execute(delete(ChatSession).where(ChatSession.agent_slug == existing.slug))
                
                # Delete agent
                logger.info(f"   -> Deleted agent: {existing.slug}")
                await session.delete(existing)
            
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

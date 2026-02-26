import sys
import os
import asyncio
import yaml
from datetime import datetime

# Add project root to sys.path to allow imports from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import async_session_factory
from models import NewsSettings
from sqlalchemy import select

async def sync_prompts():
    print("🚀 Starting NewsSettings prompt synchronization...")
    
    # Path to YAML (relative to backend/scripts or project root)
    # Trying project root first
    yaml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "default_prompts.yaml")
    
    if not os.path.exists(yaml_path):
        print(f"❌ Error: {yaml_path} not found.")
        return

    print(f"📖 Reading config from {yaml_path}...")
    with open(yaml_path, "r", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)

    # 1. Get News Agent Config
    news_agent_config = prompts.get("news_agent", {})
    if not news_agent_config:
        print("⚠️ Warning: 'news_agent' section not found in YAML.")
        # We continue to try to load other parts if available
    
    # 2. Get News Analyst Agent Config (for chat prompt)
    agents_config = prompts.get("agents", {})
    news_analyst_config = agents_config.get("news_analyst", {})
    
    async with async_session_factory() as session:
        # Check if settings exist
        result = await session.execute(select(NewsSettings).limit(1))
        settings = result.scalar_one_or_none()
        
        if not settings:
            print("📝 Creating new NewsSettings...")
            settings = NewsSettings(
                harvester_nightly_prompt = news_agent_config.get("harvester_nightly_prompt", ""),
                harvester_search_prompt = news_agent_config.get("harvester_search_prompt", ""),
                writer_prompt = news_agent_config.get("writer", {}).get("system_prompt", ""),
                news_chat_prompt = news_analyst_config.get("system_prompt", ""),
                foryou_rerank_prompt = news_agent_config.get("foryou_rerank_prompt", ""),
                allowed_tags = news_agent_config.get("allowed_tags", "AI, LLM, Robotics, Hardware, Startups, Policy, Science, Business, Generative AI, Computer Vision, NLP, MLOps, Data Science"),
                updated_at = datetime.utcnow()
            )
            session.add(settings)
        else:
            print("🔄 Force-updating existing NewsSettings from YAML...")
            # Always overwrite with YAML values if they exist
            if "harvester_nightly_prompt" in news_agent_config:
                settings.harvester_nightly_prompt = news_agent_config["harvester_nightly_prompt"]
            
            if "harvester_search_prompt" in news_agent_config:
                settings.harvester_search_prompt = news_agent_config["harvester_search_prompt"]
            
            if "writer" in news_agent_config and "system_prompt" in news_agent_config["writer"]:
                settings.writer_prompt = news_agent_config["writer"]["system_prompt"]
            
            if "system_prompt" in news_analyst_config:
                settings.news_chat_prompt = news_analyst_config["system_prompt"]

            if "allowed_tags" in news_agent_config:
                settings.allowed_tags = news_agent_config["allowed_tags"]

            if "foryou_rerank_prompt" in news_agent_config:
                settings.foryou_rerank_prompt = news_agent_config["foryou_rerank_prompt"]
                
            settings.updated_at = datetime.utcnow()
            session.add(settings)

        await session.commit()
        print("✅ Prompts synchronized successfully from YAML!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(sync_prompts())

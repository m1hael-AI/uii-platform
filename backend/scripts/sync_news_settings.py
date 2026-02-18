import asyncio
import yaml
from sqlalchemy import select, update
from database import async_session_factory
from models import NewsSettings
import os

async def sync_prompts():
    print("🚀 Starting NewsSettings prompt synchronization...")
    
    # Path to YAML
    yaml_path = "resources/default_prompts.yaml"
    if not os.path.exists(yaml_path):
        print(f"❌ Error: {yaml_path} not found.")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)

    news_prompts = prompts.get("agents", {}).get("news_agent", {})
    if not news_prompts:
        print("❌ Error: 'news_agent' prompts not found in YAML.")
        return

    async with async_session_factory() as session:
        # Check if settings exist
        result = await session.execute(select(NewsSettings).limit(1))
        settings = result.scalar_one_or_none()

        if not settings:
            print("📝 Creating new NewsSettings...")
            settings = NewsSettings(
                harvester_nightly_prompt=news_prompts.get("harvester_nightly_prompt", ""),
                harvester_search_prompt=news_prompts.get("harvester_search_prompt", ""),
                writer_prompt=prompts.get("agents", {}).get("writer", {}).get("system_prompt", ""),
                allowed_tags=news_prompts.get("allowed_tags", "AI, LLM, Robotics, Hardware, Startups, Policy, Science, Business, Generative AI, Computer Vision, NLP, MLOps, Data Science")
            )
            session.add(settings)
        else:
            print("🔄 Updating existing NewsSettings...")
            settings.harvester_nightly_prompt = news_prompts.get("harvester_nightly_prompt", settings.harvester_nightly_prompt)
            settings.harvester_search_prompt = news_prompts.get("harvester_search_prompt", settings.harvester_search_prompt)
            settings.writer_prompt = prompts.get("agents", {}).get("writer", {}).get("system_prompt", settings.writer_prompt)
            
            # Update tags if available
            if "allowed_tags" in news_prompts:
                settings.allowed_tags = news_prompts["allowed_tags"]

        await session.commit()
        print("✅ Prompts synchronized successfully!")

if __name__ == "__main__":
    asyncio.run(sync_prompts())

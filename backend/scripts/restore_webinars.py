import asyncio
import json
import sys
import os
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Webinar
from config import settings

async def restore_webinars():
    # File is in backend/webinars_dump.json, this script is in backend/scripts/
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webinars_dump.json")
    
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    print(f"Connecting to {settings.database_url}...")
    
    # Use proper async URL
    async_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("Checking existing webinars...")
        result = await db.execute(select(Webinar))
        existing = result.scalars().first()
        
        if existing:
            print("Webinars already exist in DB. Skipping restore to avoid duplicates.")
            # return 
            # Uncomment return to strictly prevent overwrite. 
            # For now, let's insert only missing IDs? Or just stop.
            print("Use --force to overwrite (not implemented). Stopping.")
            return

        print(f"Loading data from {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        count = 0
        for item in data:
            # Parse dates
            for key in ['created_at', 'updated_at', 'scheduled_at']:
                if item.get(key):
                    item[key] = datetime.fromisoformat(item[key])
            
            # Create object
            # Filter out keys not in model if any?
            # Assuming dump is 1:1 consistent with current model
            webinar = Webinar(**item)
            db.add(webinar)
            count += 1
            
        await db.commit()
        print(f"✅ Restored {count} webinars.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(restore_webinars())

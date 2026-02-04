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
        
        print(f"Loading data from {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        count = 0
        from datetime import timezone
        now = datetime.now(timezone.utc)
        import re

        for item in data:
            # Parse dates
            for key in ['created_at', 'updated_at', 'scheduled_at']:
                if item.get(key):
                    dt = datetime.fromisoformat(item[key])
                    # Ensure timezone awareness
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    item[key] = dt
            
            # Clean Video URL
            if item.get('video_url'):
                iframe_match = re.search(r'src="([^"]+)"', item['video_url'])
                if iframe_match:
                    item['video_url'] = iframe_match.group(1)

            # Fix is_upcoming
            if item.get('scheduled_at'):
                # Force recalculate status based on current time
                item['is_upcoming'] = item['scheduled_at'] > now
            
            # Upsert logic: Check if exists by ID
            webinar_id = item.get('id')
            existing_webinar = None
            if webinar_id:
               existing_webinar = await db.get(Webinar, webinar_id)
            
            if existing_webinar:
                # Update existing
                for k, v in item.items():
                    setattr(existing_webinar, k, v)
                db.add(existing_webinar)
            else:
                # Create new
                webinar = Webinar(**item)
                db.add(webinar)
            
            count += 1
            
        await db.commit()
        print(f"✅ Restored {count} webinars with cleaned data.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(restore_webinars())

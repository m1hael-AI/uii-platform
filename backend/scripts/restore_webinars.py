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

from models import WebinarSchedule, WebinarLibrary
from database import init_db
from config import settings

async def restore_webinars():
    # File is in secrets/webinars_dump.json
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secrets", "webinars_dump.json")
    
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    print(f"Connecting to {settings.database_url}...")
    
    # Use proper async URL
    async_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Ensure tables exist!
    print("Ensuring database tables exist...")
    await init_db()

    async with async_session() as db:
        print(f"Loading data from {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        schedule_count = 0
        library_count = 0
        from datetime import timezone
        now = datetime.utcnow()
        import re

        for item in data:
            # Parse dates
            for key in ['created_at', 'updated_at', 'scheduled_at']:
                if item.get(key):
                    dt = datetime.fromisoformat(item[key])
                    # Ensure we work with UTC and then strip timezone to make it "naive"
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    item[key] = dt
            
            # Clean Video URL
            if item.get('video_url'):
                iframe_match = re.search(r'src="([^"]+)"', item['video_url'])
                if iframe_match:
                    item['video_url'] = iframe_match.group(1)

            # Determine destination based on scheduled_at
            is_upcoming = False
            if item.get('scheduled_at'):
                is_upcoming = item['scheduled_at'] > now
            
            # Common fields
            base_data = {
                "title": item.get('title'),
                "description": item.get('description'),
                "thumbnail_url": item.get('thumbnail_url'),
                "speaker_name": item.get('speaker_name') or "Дмитрий Романов",  # Default speaker
                "is_published": item.get('is_published', True),
                "created_at": item.get('created_at', now),
                "updated_at": item.get('updated_at', now)
            }

            if is_upcoming:
                # Check exist
                stmt = select(WebinarSchedule).where(WebinarSchedule.title == base_data['title'])
                res = await db.execute(stmt)
                existing = res.scalar_one_or_none()
                
                if not existing:
                    new_item = WebinarSchedule(
                        **base_data,
                        connection_link=item.get('connection_link'),
                        scheduled_at=item.get('scheduled_at') or now
                    )
                    db.add(new_item)
                    schedule_count += 1
            else:
                # Check exist
                stmt = select(WebinarLibrary).where(WebinarLibrary.title == base_data['title'])
                res = await db.execute(stmt)
                existing = res.scalar_one_or_none()
                
                if not existing:
                    new_item = WebinarLibrary(
                        **base_data,
                        video_url=item.get('video_url', ""),
                        transcript_context=item.get('transcript_context', ""),
                        conducted_at=item.get('scheduled_at') or item.get('created_at', now)
                    )
                    db.add(new_item)
                    library_count += 1
            
        await db.commit()
        print(f"✅ Restored: {schedule_count} to Schedule, {library_count} to Library.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(restore_webinars())

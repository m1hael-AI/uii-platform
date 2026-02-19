import asyncio
import json
import sys
import os
from datetime import datetime, timezone
import re

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import WebinarSchedule
from database import init_db
from config import settings

async def restore_schedule_only():
    """
    Restores ONLY future webinars (schedule) from JSON dump.
    Does NOT touch WebinarLibrary (past webinars) or Vectors.
    """
    
    # File is in secrets/webinars_dump.json
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secrets", "webinars_dump.json")
    
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} not found.")
        return

    print(f"Connecting to {settings.database_url}...")
    
    # Use proper async URL
    async_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("Ensuring database tables exist...")
    await init_db()

    async with async_session() as db:
        print(f"Loading data from {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        schedule_count = 0
        skipped_count = 0
        now = datetime.utcnow()

        print(f"Current UTC time: {now}")

        for item in data:
            # Parse dates
            for key in ['created_at', 'updated_at', 'scheduled_at']:
                if item.get(key):
                    dt = datetime.fromisoformat(item[key])
                    # Ensure we work with UTC and then strip timezone to make it "naive"
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    item[key] = dt
            
            # Determine if upcoming
            scheduled_at = item.get('scheduled_at')
            if not scheduled_at:
                continue # Skip if no date

            is_upcoming = scheduled_at > now
            
            if is_upcoming:
                # Common fields
                base_data = {
                    "title": item.get('title'),
                    "description": item.get('description'),
                    "thumbnail_url": item.get('thumbnail_url'),
                    "speaker_name": item.get('speaker_name') or "Дмитрий Романов",
                    "is_published": item.get('is_published', True),
                    "created_at": item.get('created_at', now),
                    "updated_at": item.get('updated_at', now)
                }

                # Check exist
                stmt = select(WebinarSchedule).where(WebinarSchedule.title == base_data['title'])
                res = await db.execute(stmt)
                existing = res.scalar_one_or_none()
                
                if not existing:
                    new_item = WebinarSchedule(
                        **base_data,
                        connection_link=item.get('connection_link'),
                        scheduled_at=scheduled_at
                    )
                    db.add(new_item)
                    schedule_count += 1
                    print(f"➕ Adding to Schedule: {base_data['title']} ({scheduled_at})")
                else:
                    skipped_count += 1
                    # Optional: update existing? No, better safe.

        await db.commit()
        print(f"✅ DONE: Added {schedule_count} future webinars. Skipped {skipped_count} existing.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(restore_schedule_only())

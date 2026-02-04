import asyncio
import sys
import os
from datetime import datetime, timedelta
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import WebinarSchedule, WebinarLibrary
from config import settings

async def fix_dates():
    print(f"Connecting to {settings.database_url}...")
    
    async_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 1. Find the lost webinars in Library
        titles_to_fix = [
            "Введение в нейросети: С чего начать?",
            "Промпт-инжиниринг: Как говорить с AI"
        ]
        
        for title in titles_to_fix:
            stmt = select(WebinarLibrary).where(WebinarLibrary.title == title)
            res = await db.execute(stmt)
            library_item = res.scalar_one_or_none()
            
            if library_item:
                print(f"Found '{title}' in Library. Moving to Schedule...")
                
                # Create Schedule item
                # Set date to future: +7 days from now (approx)
                new_date = datetime.utcnow() + timedelta(days=7)
                
                new_schedule = WebinarSchedule(
                    title=library_item.title,
                    description=library_item.description,
                    thumbnail_url=library_item.thumbnail_url,
                    speaker_name=library_item.speaker_name,
                    is_published=library_item.is_published,
                    scheduled_at=new_date,
                    duration_minutes=60, # Default
                    connection_link="https://meet.google.com/example", # Placeholder
                    reminder_1h_sent=False,
                    reminder_15m_sent=False
                )
                
                db.add(new_schedule)
                
                # Delete from Library
                await db.delete(library_item)
                print(f"✅ Moved '{title}' to Schedule (Date: {new_date})")
            else:
                print(f"⚠️ '{title}' not found in Library (maybe already fixed?)")
        
        await db.commit()
        print("Done!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_dates())

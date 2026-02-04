import asyncio
import sys
import os
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, delete

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import WebinarSchedule, WebinarLibrary, WebinarSignup, ChatSession
from config import settings

async def migrate():
    print(f"Connecting to database...")
    async_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 1. Fetch old webinars
        print("Fetching data from old 'webinars' table...")
        try:
            result = await db.execute(text("SELECT * FROM webinars"))
            old_webinars = result.mappings().all()
        except Exception as e:
            print(f"Error fetching old webinars: {e}")
            return

        print(f"Found {len(old_webinars)} webinars to migrate.")

        schedule_count = 0
        library_count = 0
        
        # Mapping for foreign keys: {old_id: (new_id, type)}
        id_mapping = {}

        for old in old_webinars:
            # Determine where it goes
            is_upcoming = old.get('is_upcoming', False)
            
            # Common fields
            data = {
                "title": old['title'],
                "description": old['description'],
                "thumbnail_url": old['thumbnail_url'],
                "speaker_name": old['speaker_name'],
                "is_published": old['is_published'],
                "created_at": old['created_at'],
                "updated_at": old['updated_at']
            }

            if is_upcoming:
                # To Schedule
                new_item = WebinarSchedule(
                    **data,
                    connection_link=old['connection_link'],
                    scheduled_at=old['scheduled_at'] or datetime.utcnow(),
                    duration_minutes=old['duration_minutes'] or 60,
                    reminder_1h_sent=old['reminder_1h_sent'],
                    reminder_15m_sent=old['reminder_15m_sent']
                )
                db.add(new_item)
                await db.flush() # Get ID
                id_mapping[old['id']] = (new_item.id, "schedule")
                schedule_count += 1
            else:
                # To Library
                new_item = WebinarLibrary(
                    **data,
                    video_url=old['video_url'] or "",
                    transcript_context=old['transcript_context'] or "",
                    conducted_at=old['scheduled_at'] or old['created_at']
                )
                db.add(new_item)
                await db.flush() # Get ID
                id_mapping[old['id']] = (new_item.id, "library")
                library_count += 1

        print(f"Moving Signups...")
        # 2. Update Signups
        result_signups = await db.execute(text("SELECT * FROM webinar_signups"))
        old_signups = result_signups.mappings().all()
        
        # Clear existing (we'll re-insert to handle foreign key changes)
        # Note: WebinarSignup model now has schedule_id
        await db.execute(delete(WebinarSignup))
        
        for signup in old_signups:
            old_web_id = signup['webinar_id']
            if old_web_id in id_mapping:
                new_id, target_type = id_mapping[old_web_id]
                if target_type == "schedule":
                    new_signup = WebinarSignup(
                        user_id=signup['user_id'],
                        schedule_id=new_id,
                        reminder_1h_sent=signup['reminder_1h_sent'],
                        reminder_start_sent=signup['reminder_start_sent'],
                        created_at=signup['created_at']
                    )
                    db.add(new_signup)

        print(f"Updating Chat Sessions...")
        # 3. Update Chat Sessions
        result_chats = await db.execute(text("SELECT * FROM chat_sessions"))
        old_chats = result_chats.mappings().all()
        
        # We can't delete chat sessions easily due to messages, let's update them
        for chat in old_chats:
            old_web_id = chat['webinar_id']
            if old_web_id and old_web_id in id_mapping:
                new_id, target_type = id_mapping[old_web_id]
                update_stmt = text(f"UPDATE chat_sessions SET {target_type}_id = :new_id, webinar_id = NULL WHERE id = :chat_id")
                await db.execute(update_stmt, {"new_id": new_id, "chat_id": chat['id']})

        await db.commit()
        print(f"✅ Migration complete!")
        print(f"   - Schedule: {schedule_count}")
        print(f"   - Library: {library_count}")
        print(f"   - Signups: {len(old_signups)}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate())

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import WebinarSchedule, WebinarLibrary
from config import settings

async def verify():
    print(f"Connecting to database...")
    async_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("\n--- Model Verification ---")
        try:
            # Check Schedule
            res_s = await db.execute(text("SELECT count(*) FROM webinar_schedules"))
            s_count = res_s.scalar()
            print(f"WebinarSchedule table exists. Count: {s_count}")
            
            # Check Library
            res_l = await db.execute(text("SELECT count(*) FROM webinar_libraries"))
            l_count = res_l.scalar()
            print(f"WebinarLibrary table exists. Count: {l_count}")
            
            # Check foreign keys in Signups
            res_signup = await db.execute(text("SELECT count(*) FROM webinar_signups WHERE schedule_id IS NOT NULL"))
            signup_count = res_signup.scalar()
            print(f"WebinarSignup table updated with schedule_id. Valid signups: {signup_count}")

            # Check foreign keys in ChatSessions
            res_chat = await db.execute(text("SELECT count(*) FROM chat_sessions WHERE schedule_id IS NOT NULL OR library_id IS NOT NULL"))
            chat_count = res_chat.scalar()
            print(f"ChatSession table updated with new IDs. Relinked sessions: {chat_count}")

        except Exception as e:
            print(f"Verification failed (likely tables don't exist yet): {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify())

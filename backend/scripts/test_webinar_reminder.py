
import asyncio
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from models import Webinar, User, SystemConfig
from database import async_engine
from config import settings
from aiogram import Bot

# Mock Templates (later from SystemConfig)
DEFAULT_TEMPLATE_1H = """
⏰ <b>Напоминание: Вебинар через 1 час!</b>

Тема: <b>{title}</b>
Начало: {time} ({date})

🔗 <a href="{link}">Подключиться к трансляции</a>

<i>Не опаздывайте!</i>
"""

async def test_send_reminder(target_user_id: int):
    print(f"🚀 Starting Test Reminder for User ID: {target_user_id}...")
    
    # 1. Setup DB Session
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Fetch Template from DB settings
        stmt = select(SystemConfig).where(SystemConfig.key == "webinar_reminder_1h_template")
        result = await session.execute(stmt)
        config_entry = result.scalar_one_or_none()
        
        template = config_entry.value if config_entry else DEFAULT_TEMPLATE_1H

        # 2. Get Upcoming Webinar
        query = select(Webinar).where(Webinar.is_upcoming == True).order_by(Webinar.scheduled_at)
        result = await session.execute(query)
        webinar = result.scalars().first()
        
        if not webinar:
            print("❌ No upcoming webinars found in DB. Create one first!")
            return

        print(f"✅ Found Webinar: {webinar.title} (ID: {webinar.id})")
        
        # 3. Prepare Data
        connection_link = webinar.connection_link or webinar.video_url or "https://example.com/no-link"
        scheduled_at = webinar.scheduled_at 
        # Format time (Assume stored as UTC, convert to User Timezone? For now just UTC+3 MSK)
        # Quick hack for MSK
        msk_time = scheduled_at # + 3 hours if naive?
        # Assuming timestamps in DB are UTC.
        
        formatted_time = msk_time.strftime("%H:%M")
        formatted_date = msk_time.strftime("%d.%m.%Y")
        
        # 4. Format Message
        try:
            message_text = template.format(
                title=webinar.title,
                time=formatted_time,
                date=formatted_date,
                link=connection_link
            )
        except KeyError as e:
            print(f"❌ Template Error: Missing key {e}")
            message_text = f"Error in template: {e}"
        
        print(f"📝 Message Preview:\n---\n{message_text}\n---")
        
        # 5. Send via Bot
        bot = Bot(token=settings.telegram_bot_token)
        try:
            print(f"📨 Sending to Telegram ID: {target_user_id}...")
            await bot.send_message(
                chat_id=target_user_id,
                text=message_text,
                parse_mode="HTML"
            )
            print("✅ Message Sent Successfully!")
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
        finally:
            await bot.session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.test_webinar_reminder <TELEGRAM_USER_ID>")
        sys.exit(1)
        
    user_id = int(sys.argv[1])
    asyncio.run(test_send_reminder(user_id))

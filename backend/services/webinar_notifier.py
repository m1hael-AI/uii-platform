import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from loguru import logger
from aiogram import Bot

from models import WebinarSchedule, WebinarSignup, SystemConfig
from config import settings

# Default Templates
DEFAULT_TEMPLATE_1H = """
⏰ <b>Напоминание: Вебинар через 1 час!</b>

Тема: <b>{title}</b>
Начало: {time} ({date})

🔗 <a href="{link}">Подключиться к трансляции</a>

<i>Не опаздывайте!</i>
"""

DEFAULT_TEMPLATE_START = """
🔴 <b>Вебинар начинается прямо сейчас!</b>

Тема: <b>{title}</b>

🔗 <a href="{link}">>>> ВОЙТИ В КОМНАТУ <<<</a>

<i>Ждем только вас!</i>
"""

async def check_webinar_reminders(db: AsyncSession):
    """
    Проверяет ближайшие вебинары и рассылает уведомления.
    Запускается планировщиком каждую минуту.
    """
    now = datetime.utcnow()
    
    # 1. Fetch Templates (once per run)
    stmt_1h = select(SystemConfig).where(SystemConfig.key == "webinar_reminder_1h_template")
    res_1h = await db.execute(stmt_1h)
    conf_1h = res_1h.scalar_one_or_none()
    template_1h = conf_1h.value if conf_1h else DEFAULT_TEMPLATE_1H
    
    stmt_start = select(SystemConfig).where(SystemConfig.key == "webinar_reminder_start_template")
    res_start = await db.execute(stmt_start)
    conf_start = res_start.scalar_one_or_none()
    template_start = conf_start.value if conf_start else DEFAULT_TEMPLATE_START

    # 2. Get Upcoming Webinars from Schedule
    query = select(WebinarSchedule).where(WebinarSchedule.is_published == True)
    result = await db.execute(query)
    webinars = result.scalars().all()
    
    bot = Bot(token=settings.telegram_bot_token)
    
    try:
        for webinar in webinars:
            if not webinar.scheduled_at:
                continue
                
            time_diff = webinar.scheduled_at - now
            minutes_left = time_diff.total_seconds() / 60
            
            # === 1 HOUR REMINDER (55-65 mins) ===
            # Проверяем диапазон, чтобы не спамить, если крон пропустил минуту, но не слишком широко
            if 50 <= minutes_left <= 65 and not webinar.reminder_1h_sent:
                logger.info(f"⏰ Sending 1h reminder for webinar {webinar.id} ({minutes_left:.1f} min left)")
                await send_notifications(db, bot, webinar, template_1h, "1h")
                
                # Mark Global Flag
                webinar.reminder_1h_sent = True
                db.add(webinar)
                await db.commit()
                
            # === START REMINDER (0-10 mins) ===
            elif 0 <= minutes_left <= 10 and not webinar.reminder_15m_sent: # Using 15m field for "start"? Or create new field?
                # The model has remainder_15m_sent. Let's use it as "Start/15m" reminder.
                logger.info(f"🔴 Sending Start reminder for webinar {webinar.id} ({minutes_left:.1f} min left)")
                await send_notifications(db, bot, webinar, template_start, "start")
                
                # Mark Global Flag
                webinar.reminder_15m_sent = True # Reuse this field
                db.add(webinar)
                await db.commit()
                
    finally:
        await bot.session.close()

async def send_notifications(db: AsyncSession, bot: Bot, webinar: Webinar, template: str, type: str):
    """
    Отправляет уведомления подписчикам
    type: "1h" or "start"
    """
    # 1. Prepare Message
    connection_link = webinar.connection_link or webinar.video_url or "#"
    # Convert UTC to MSK (UTC+3) manually for display
    msk_time = webinar.scheduled_at + timedelta(hours=3)
    formatted_time = msk_time.strftime("%H:%M")
    formatted_date = msk_time.strftime("%d.%m.%Y")
    
    try:
        message_text = template.format(
            title=webinar.title,
            time=formatted_time,
            date=formatted_date,
            link=connection_link
        )
    except Exception as e:
        logger.error(f"Template formatting error: {e}")
        message_text = f"Reminder: {webinar.title} starts at {formatted_time}. Link: {connection_link}"

    # 2. Get Targets
    query = select(WebinarSignup).where(
        WebinarSignup.schedule_id == webinar.id
    ).join(WebinarSignup.user) # Ensure user exists
    
    result = await db.execute(query)
    signups = result.scalars().all()
    
    count = 0
    for signup in signups:
        # Check per-user flag
        if type == "1h" and signup.reminder_1h_sent:
            continue
        if type == "start" and signup.reminder_start_sent:
            continue
            
        user = await db.get(User, signup.user_id) # Should be joined ideally
        if not user or not user.tg_id:
            continue
            
        try:
            await bot.send_message(
                chat_id=user.tg_id,
                text=message_text,
                parse_mode="HTML"
            )
            # Mark Sent
            if type == "1h":
                signup.reminder_1h_sent = True
            elif type == "start":
                signup.reminder_start_sent = True
            
            db.add(signup)
            count += 1
        except Exception as e:
            logger.warning(f"Failed to send to user {user.id}: {e}")
            
    await db.commit()
    logger.info(f"✅ Sent {type} notifications to {count} users for webinar {webinar.id}")

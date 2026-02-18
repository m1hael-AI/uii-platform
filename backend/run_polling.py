import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.enums import ParseMode

from config import settings
from bot.router import router as main_router
# from database import create_db_and_tables

from utils.logger import logger

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# Setup logging interception
logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
# Remove standard handlers if any
logging.getLogger().handlers = [InterceptHandler()]


async def main():
    logger.info("Starting Bot in POLLING mode...")
    
    # 1. Init DB (ensure tables exist)
    # Skipping table creation here as it uses sync engine with async driver causing MissingGreenlet.
    # Tables are created by the main backend service anyway.
    # await create_db_and_tables()
    
    # 2. Setup Storage
    storage = None
    if settings.redis_url:
        storage = RedisStorage.from_url(settings.redis_url)
        logger.info("Using Redis Storage")
    else:
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()
        logger.warning("Using Memory Storage (Redis not found)")

    # 3. Init Bot & Dispatcher
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=storage)
    
    # 4. Include Routers
    dp.include_router(main_router)
    
    # 5. Delete Webhook (to switch to polling)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted. Starting polling...")
    
    # 6. Start Polling with custom timeout for stability
    # Explicitly using long polling timeout to match standard Telegram API expectations
    # and reduce 'Connection reset' frequency.
    try:
        await dp.start_polling(
            bot, 
            polling_timeout=30,  # 30 seconds wait for updates
            handle_signals=False # Handled manually in current setup or docker
        )
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")

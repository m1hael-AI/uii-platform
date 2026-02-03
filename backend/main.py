"""
Главный файл FastAPI приложения AI University.
Здесь только:
- Инициализация приложения
- CORS настройки
- Lifespan events (startup/shutdown)
- Webhook endpoint для Telegram
- Подключение роутеров

Логика бота вынесена в backend/bot/
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import logger
from config import settings
from bot.loader import bot, dp
from routers import users, chat, auth, password_reset, admin, webinars


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    События при старте и остановке приложения.
    Startup: создаём таблицы БД, устанавливаем webhook для Telegram, запускаем scheduler
    Shutdown: удаляем webhook, останавливаем scheduler
    """
    logger.info("Запуск AI University Backend...")
    
    # Telegram webhook setup DISABLED (Using Polling in separate service)
    # if settings.telegram_bot_token and settings.telegram_webhook_url:
    #     try:
    #         webhook_url = f"{settings.telegram_webhook_url}/webhook"
    #         await bot.set_webhook(
    #             url=webhook_url,
    #             secret_token=settings.telegram_webhook_secret,
    #             drop_pending_updates=True
    #         )
    #         logger.info(f"Telegram webhook установлен: {webhook_url}")
    #     except Exception as e:
    #         logger.error(f"Ошибка установки webhook: {e}")
    # else:
    logger.info("Telegram Webhook отключен (используется Polling в отдельном контейнере)")
    
    # Запускаем планировщик проактивности
    try:
        from services.scheduler import start_scheduler
        start_scheduler()
        logger.info("Планировщик проактивности запущен")
    except Exception as e:
        logger.error(f"Ошибка запуска планировщика: {e}")
    
    yield
    
    logger.info("Остановка AI University Backend...")
    
    # Останавливаем планировщик
    try:
        from services.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("Планировщик проактивности остановлен")
    except Exception as e:
        logger.error(f"Ошибка остановки планировщика: {e}")
    
    if settings.telegram_bot_token:
        try:
            await bot.delete_webhook()
            await bot.session.close()
            logger.info("Telegram webhook удалён")
        except Exception as e:
            logger.error(f"Ошибка удаления webhook: {e}")


app = FastAPI(
    title=settings.app_name,
    description="Образовательная платформа с проактивными AI-агентами",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Include routers
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(password_reset.router)
app.include_router(admin.router)
app.include_router(webinars.router)



# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     """
#     Middleware для логирования всех запросов:
#     - Log request method and URL
#     - Execute request
#     - Log response status and process time
#     - Catch and log unhandled exceptions
#     """
#     import time
#     start_time = time.time()
    
#     # Log request start
#     logger.info(f"Incoming request: {request.method} {request.url.path}")
    
#     try:
#         response = await call_next(request)
#         process_time = (time.time() - start_time) * 1000
        
#         # Log response
#         logger.info(
#             f"Request completed: {request.method} {request.url.path} "
#             f"- Status: {response.status_code} - Time: {process_time:.2f}ms"
#         )
#         return response
#     except Exception as e:
#         # Log unhandled exception
#         process_time = (time.time() - start_time) * 1000
#         logger.error(
#             f"Request failed: {request.method} {request.url.path} "
#             f"- Error: {str(e)} - Time: {process_time:.2f}ms"
#         )
#         # Re-raise to let FastAPI handle it (or return 500 custom response)
#         raise e


@app.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    """
    Endpoint для получения обновлений от Telegram.
    Передаём update в Dispatcher для обработки.
    """
    if settings.telegram_webhook_secret:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != settings.telegram_webhook_secret:
            logger.warning("Неверный secret token в webhook запросе")
            return Response(status_code=403)
    
    try:
        update_data = await request.json()
        
        from aiogram.types import Update
        update = Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot, update)
        
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return Response(status_code=500)


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервера"""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": f"Добро пожаловать в {settings.app_name}!",
        "docs": "/docs" if settings.debug else "disabled",
    }

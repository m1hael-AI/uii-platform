"""
Инициализация подключения к базе данных.
Vendor-agnostic: работает с любым PostgreSQL через стандартный connection string.
"""

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings


# === СИНХРОННЫЙ ENGINE (для миграций и простых операций) ===
sync_engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)


# === АСИНХРОННЫЙ ENGINE (для production) ===
# Конвертируем postgresql:// в postgresql+asyncpg://
async_database_url = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)

async_engine = create_async_engine(
    async_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

# Фабрика асинхронных сессий
async_session_factory = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Создаёт таблицы, если их нет"""
    async with async_engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # DEBUG ONLY
        await conn.run_sync(SQLModel.metadata.create_all)


def get_sync_session():
    """Возвращает синхронную сессию (для простых операций)"""
    with Session(sync_engine) as session:
        yield session


async def get_async_session():
    """Возвращает асинхронную сессию (для FastAPI endpoints)"""
    async with async_session_factory() as session:
        yield session

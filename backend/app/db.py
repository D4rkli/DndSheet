import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings

def _db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        # Render часто даёт postgres://..., а asyncpg ждёт postgresql+asyncpg://...
        url = url.replace("postgres://", "postgresql+asyncpg://")
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    # локально оставляем твой текущий SQLite путь из settings
    return settings.SQLITE_PATH

engine = create_async_engine(_db_url(), echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with SessionLocal() as session:
        yield session

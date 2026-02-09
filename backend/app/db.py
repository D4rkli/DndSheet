import os
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from .config import settings
from .models import Base  # ВАЖНО: используем Base из models.py


def _db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        url = url.replace("postgres://", "postgresql+asyncpg://")
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        return url
    return settings.SQLITE_PATH


engine = create_async_engine(_db_url(), echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def _sqlite_self_heal(conn) -> None:
    """
    Для режима без Alembic:
    - create_all() не добавляет новые колонки в существующие таблицы
    - поэтому если видим, что нужной колонки нет — переносим БД в бэкап и создаём заново.
    """
    url = _db_url()
    if not url.startswith("sqlite"):
        return  # self-heal делаем только для sqlite

    # вытащим путь к файлу sqlite из url вида sqlite+aiosqlite:///./dnd_v2.sqlite3
    db_file = url.split("///", 1)[-1]
    db_file = os.path.abspath(db_file)

    # если таблицы ещё нет — ок, create_all её создаст
    res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='characters'"))
    if res.scalar_one_or_none() is None:
        return

    # проверим наличие колонки xp_per_level (можешь сюда добавлять новые обязательные колонки)
    cols = await conn.execute(text("PRAGMA table_info(characters)"))
    col_names = {row[1] for row in cols.fetchall()}  # row[1] = name

    required = {"xp_per_level"}  # добавляй сюда новые поля, которые ты ввела в models.py
    if required.issubset(col_names):
        return  # схема ок

    # схема устарела -> унесём старую БД и создадим новую
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(db_file), "db_backups")
    os.makedirs(backup_dir, exist_ok=True)

    backup_path = os.path.join(backup_dir, f"dnd_v2.sqlite3.{ts}.bak")

    # закрываем текущий коннект транзакции и переносим файл
    # (мы уже внутри engine.begin(), поэтому просто сообщим и потом удалим файл снаружи)
    # Для простоты: пометим, что надо пересоздать — через исключение
    raise RuntimeError(f"SQLITE_SCHEMA_OUTDATED::{db_file}::{backup_path}")


async def init_db():
    # импорт моделей, чтобы SQLAlchemy "увидел" все таблицы
    import app.models  # noqa: F401  :contentReference[oaicite:4]{index=4}

    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            await _sqlite_self_heal(conn)
        except RuntimeError as e:
            msg = str(e)
            if msg.startswith("SQLITE_SCHEMA_OUTDATED::"):
                _, db_file, backup_path = msg.split("::", 2)

                # переносим файл БД
                if os.path.exists(db_file):
                    os.replace(db_file, backup_path)

                # создаём заново
                await conn.run_sync(Base.metadata.create_all)
            else:
                raise

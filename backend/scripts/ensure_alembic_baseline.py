"""Exit 0 if the DB already has an alembic_version table, exit 1 otherwise.

Used by the deploy script to decide whether this database needs to be
stamped at the pre-existing baseline revision before running
`alembic upgrade head` for the first time (it was originally built via
SQLAlchemy's create_all(), not tracked by Alembic).
"""
import os
import sys

# Make sure `backend/` (this script's parent dir) is importable as the
# `app` package root, regardless of the caller's cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect

if not (url := os.getenv("DATABASE_URL")):
    from app.config import settings
    url = settings.SQLITE_PATH
url = url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
url = url.replace("sqlite+aiosqlite://", "sqlite://")

insp = inspect(create_engine(url))
sys.exit(0 if "alembic_version" in insp.get_table_names() else 1)

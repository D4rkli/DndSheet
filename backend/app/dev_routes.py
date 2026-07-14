from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .deps import require_dev
from .security import SESSION_COOKIE_NAME, create_session_cookie
from .config import settings
from .models import (
    User,
    Character,
    Campaign,
    CampaignMessage,
    CampaignBattle,
    FeedbackReport,
    AccessCode,
)
from . import crud, schemas

router = APIRouter()

_COUNT_TABLES = {
    "users": User,
    "characters": Character,
    "campaigns": Campaign,
    "campaign_messages": CampaignMessage,
    "campaign_battles": CampaignBattle,
    "feedback_reports": FeedbackReport,
    "access_codes": AccessCode,
}


@router.get("/stats", dependencies=[Depends(require_dev)])
async def dev_stats(db: AsyncSession = Depends(get_db)):
    stats = {}
    for name, model in _COUNT_TABLES.items():
        result = await db.execute(select(func.count()).select_from(model))
        stats[name] = result.scalar_one()
    return stats


@router.get("/info", dependencies=[Depends(require_dev)])
async def dev_info(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        revision = row[0] if row else None
    except Exception:
        # e.g. a fresh install bootstrapped via create_all(), never alembic-stamped
        revision = None

    return {
        "server_time": datetime.utcnow().isoformat() + "Z",
        "alembic_revision": revision,
    }


@router.post("/login-as")
async def login_as(
    body: schemas.DevLoginAs,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _dev: User = Depends(require_dev),
):
    user = await crud.get_or_create_user(db, tg_id=body.tg_id, first_name=body.first_name)

    token = create_session_cookie("telegram", user.tg_id, first_name=body.first_name)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE_DAYS * 86400,
        path="/",
    )
    return {"status": "ok", "tg_id": user.tg_id}


@router.post("/access-codes")
async def create_access_code(
    body: schemas.GenerateAccessCode,
    db: AsyncSession = Depends(get_db),
    dev: User = Depends(require_dev),
):
    entry = await crud.generate_access_code(db, dev.id, body.duration_days)
    return {"code": entry.code, "duration_days": entry.duration_days}


@router.get("/access-codes")
async def list_access_codes(
    db: AsyncSession = Depends(get_db),
    _dev: User = Depends(require_dev),
):
    q = await db.execute(select(AccessCode).order_by(AccessCode.created_at.desc()).limit(50))
    codes = q.scalars().all()
    return [
        {
            "code": c.code,
            "duration_days": c.duration_days,
            "created_at": c.created_at.isoformat(),
            "redeemed_by_user_id": c.redeemed_by_user_id,
            "redeemed_at": c.redeemed_at.isoformat() if c.redeemed_at else None,
        }
        for c in codes
    ]

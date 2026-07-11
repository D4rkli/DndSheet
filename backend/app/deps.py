import json

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .security import SESSION_COOKIE_NAME, read_session_cookie, verify_telegram_init_data
from .models import User
from . import crud


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
) -> User:
    """Resolve the current user from either Telegram Mini App initData
    (X-TG-INIT-DATA header) or a website session cookie."""
    if x_tg_init_data:
        try:
            data = verify_telegram_init_data(x_tg_init_data)
            user_json = data.get("user")
            if not user_json:
                raise ValueError("No user in initData")
            tg_id = int(json.loads(user_json)["id"])
        except Exception as e:
            print("INIT DATA ERROR:", repr(e))
            raise HTTPException(401, "Bad Telegram initData")
    else:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        tg_id = read_session_cookie(token) if token else None
        if tg_id is None:
            raise HTTPException(401, "Not authenticated")

    return await crud.get_or_create_user(db, tg_id=tg_id)
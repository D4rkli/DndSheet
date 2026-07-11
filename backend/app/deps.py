import json

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .security import SESSION_COOKIE_NAME, read_session_cookie, verify_telegram_init_data
from .models import User
from . import crud


async def resolve_auth_profile(
    request: Request,
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
) -> dict:
    """Resolve the current authenticated profile from either Telegram Mini App
    initData (X-TG-INIT-DATA header) or a website session cookie (set after
    Telegram Login Widget or VK OAuth).

    Returns {"provider", "user_key", "first_name", "last_name", "username", "photo_url"}.
    """
    if x_tg_init_data:
        try:
            data = verify_telegram_init_data(x_tg_init_data)
            user_json = data.get("user")
            if not user_json:
                raise ValueError("No user in initData")
            tg_user = json.loads(user_json)
            return {
                "provider": "telegram",
                "user_key": int(tg_user["id"]),
                "first_name": tg_user.get("first_name"),
                "last_name": tg_user.get("last_name"),
                "username": tg_user.get("username"),
                "photo_url": tg_user.get("photo_url"),
            }
        except Exception as e:
            print("INIT DATA ERROR:", repr(e))
            raise HTTPException(401, "Bad Telegram initData")

    token = request.cookies.get(SESSION_COOKIE_NAME)
    profile = read_session_cookie(token) if token else None
    if profile is None:
        raise HTTPException(401, "Not authenticated")
    return profile


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    profile: dict = Depends(resolve_auth_profile),
) -> User:
    if profile["provider"] == "vk":
        return await crud.get_or_create_user_by_vk(db, vk_id=profile["user_key"])
    return await crud.get_or_create_user(db, tg_id=profile["user_key"])

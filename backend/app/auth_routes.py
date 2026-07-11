from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from .config import settings
from .security import (
    SESSION_COOKIE_NAME,
    create_session_cookie,
    verify_telegram_login_widget,
)

router = APIRouter()


class TelegramLoginIn(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


@router.post("/telegram-login")
async def telegram_login(body: TelegramLoginIn, response: Response):
    try:
        tg_id = verify_telegram_login_widget(body.model_dump())
    except ValueError:
        raise HTTPException(401, "Bad Telegram login data")

    token = create_session_cookie(tg_id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE_DAYS * 86400,
        path="/",
    )
    return {"status": "ok", "tg_id": tg_id}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}
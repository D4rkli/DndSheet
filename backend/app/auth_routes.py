import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_db
from . import crud
from .security import (
    SESSION_COOKIE_NAME,
    VK_STATE_COOKIE_NAME,
    create_session_cookie,
    create_vk_state_cookie,
    read_vk_state_cookie,
    verify_telegram_login_widget,
)
from .vk_oauth import build_vk_authorize_url, exchange_vk_code

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
        profile = verify_telegram_login_widget(body.model_dump())
    except ValueError:
        raise HTTPException(401, "Bad Telegram login data")

    token = create_session_cookie(
        "telegram",
        profile["tg_id"],
        first_name=profile["first_name"],
        last_name=profile["last_name"],
        username=profile["username"],
        photo_url=profile["photo_url"],
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE_DAYS * 86400,
        path="/",
    )
    return {"status": "ok", "tg_id": profile["tg_id"]}


@router.get("/vk/login")
async def vk_login():
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(url=build_vk_authorize_url(state))
    response.set_cookie(
        key=VK_STATE_COOKIE_NAME,
        value=create_vk_state_cookie(state),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/vk/callback")
async def vk_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not code or not state:
        raise HTTPException(400, "Missing code or state")

    expected_state = read_vk_state_cookie(request.cookies.get(VK_STATE_COOKIE_NAME))
    if not expected_state or not secrets.compare_digest(expected_state, state):
        raise HTTPException(401, "Bad VK OAuth state")

    try:
        profile = await exchange_vk_code(code)
    except ValueError:
        raise HTTPException(401, "VK login failed")

    await crud.get_or_create_user_by_vk(db, vk_id=profile["vk_id"])

    token = create_session_cookie(
        "vk",
        profile["vk_id"],
        first_name=profile["first_name"],
        last_name=profile["last_name"],
        username=profile["username"],
        photo_url=profile["photo_url"],
    )
    response = RedirectResponse(url="/webapp/index.html")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE_DAYS * 86400,
        path="/",
    )
    response.delete_cookie(VK_STATE_COOKIE_NAME, path="/")
    return response


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}

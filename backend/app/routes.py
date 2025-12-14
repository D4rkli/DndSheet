import json
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from .db import get_db
from .security import verify_telegram_init_data
from .config import settings
from . import crud, schemas

router = APIRouter()

def _auth_user(x_tg_init_data: str | None):
    if not x_tg_init_data:
        raise HTTPException(401, "Missing X-TG-INIT-DATA")

    try:
        data = verify_telegram_init_data(x_tg_init_data)
        user_json = data.get("user")
        if not user_json:
            raise ValueError("No user in initData")
        return json.loads(user_json)

    except Exception as e:
        print("INIT DATA ERROR:", repr(e))
        raise HTTPException(401, "Bad Telegram initData")


@router.get("/me")
async def me(
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))
    return {"tg": tg_user, "user_id": u.id, "is_dm": int(tg_user["id"]) in settings.dm_ids()}

@router.get("/characters")
async def list_characters(
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    chars = await crud.list_characters(db, u.id)

    return [
        {
            "id": c.id,
            "name": c.name,
            "race": c.race,
            "klass": c.klass,
            "level": c.level,
        }
        for c in chars
    ]


@router.get("/characters/{character_id}")
async def get_character(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character(db, character_id, u.id)
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")

    return {
        "id": ch.id,
        "name": ch.name,
        "race": ch.race,
        "klass": ch.klass,
        "level": ch.level,
    }


@router.patch("/characters/{character_id}")
async def update_character(
    character_id: int,
    body: schemas.CharacterUpdate,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.update_character(db, character_id, u.id, body)
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")

    return ch

@router.post("/characters")
async def create_character(
    body: schemas.CharacterCreate,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))
    ch = await crud.create_character(db, u.id, body.name)
    return {"id": ch.id, "name": ch.name}

@router.post("/characters/{ch_id}/items")
async def add_item(
    ch_id: int,
    body: schemas.ItemCreate,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))
    ch = await crud.get_character(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    # владелец или DM может добавлять
    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    it = await crud.add_item(db, ch_id, body.name, body.description, body.stats)
    return {"id": it.id}

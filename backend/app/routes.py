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

    ch = await crud.get_character_for_user(db, character_id, u.id)
    if not ch:
        raise HTTPException(status_code=404, detail="Character not found")

    # отдаём расширенный лист (чтобы webapp мог рисовать все поля)
    return {
        "id": ch.id,
        "name": ch.name,
        "race": ch.race,
        "gender": ch.gender,
        "klass": ch.klass,
        "level": ch.level,
        "xp": ch.xp,

        # ресурсы
        "hp": ch.hp,
        "mana": ch.mana,
        "energy": ch.energy,
        "hp_max": ch.hp_max,
        "mana_max": ch.mana_max,
        "energy_max": ch.energy_max,
        "hp_per_level": ch.hp_per_level,
        "mana_per_level": ch.mana_per_level,
        "energy_per_level": ch.energy_per_level,

        # характер
        "aggression_kindness": ch.aggression_kindness,
        "intellect": ch.intellect,
        "fearlessness": ch.fearlessness,
        "humor": ch.humor,
        "emotionality": ch.emotionality,
        "sociability": ch.sociability,
        "responsibility": ch.responsibility,
        "intimidation": ch.intimidation,
        "attentiveness": ch.attentiveness,
        "learnability": ch.learnability,
        "luck": ch.luck,
        "stealth": ch.stealth,

        # боёвка
        "initiative": ch.initiative,
        "attack": ch.attack,
        "counterattack": ch.counterattack,
        "steps": ch.steps,
        "defense": ch.defense,
        "perm_armor": ch.perm_armor,
        "temp_armor": ch.temp_armor,
        "action_points": ch.action_points,
        "dodges": ch.dodges,

        "level_up_rules": ch.level_up_rules,
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
    ch = await crud.get_character_for_user(db, ch_id, u.id)
    if not ch:
        raise HTTPException(404, "Character not found")

    # владелец или DM может добавлять
    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    it = await crud.add_item(db, ch_id, body.name, body.description, body.stats)
    return {"id": it.id}

@router.get("/characters/{ch_id}/items")
async def list_items(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    items = await crud.list_items(db, ch_id)

    return [
        {
            "id": i.id,
            "name": i.name,
            "description": i.description,
            "stats": i.stats,
        }
        for i in items
    ]

@router.delete("/characters/{ch_id}/items/{item_id}")
async def delete_item(
    ch_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    # доступ: владелец или DM
    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    ok = await crud.delete_item(db, item_id)
    if not ok:
        raise HTTPException(404, "Item not found")

    return {"status": "deleted"}


# =========================
# SPELLS
# =========================

@router.get("/characters/{ch_id}/spells")
async def list_spells(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    spells = await crud.list_spells(db, ch_id)
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "range": s.range,
            "duration": s.duration,
            "cost": s.cost,
        }
        for s in spells
    ]


@router.post("/characters/{ch_id}/spells")
async def add_spell(
    ch_id: int,
    body: schemas.SpellCreate,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_for_user(db, ch_id, u.id)
    if not ch:
        # DM может добавлять не только своим
        ch = await crud.get_character_by_id(db, ch_id)

    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    sp = await crud.add_spell(db, ch_id, body.model_dump())
    return {"id": sp.id}


@router.delete("/characters/{ch_id}/spells/{spell_id}")
async def delete_spell(
    ch_id: int,
    spell_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    ok = await crud.delete_spell(db, spell_id)
    if not ok:
        raise HTTPException(404, "Spell not found")
    return {"status": "deleted"}


# =========================
# ABILITIES
# =========================

@router.get("/characters/{ch_id}/abilities")
async def list_abilities(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    abilities = await crud.list_abilities(db, ch_id)
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "range": a.range,
            "duration": a.duration,
            "cost": a.cost,
        }
        for a in abilities
    ]


@router.post("/characters/{ch_id}/abilities")
async def add_ability(
    ch_id: int,
    body: schemas.AbilityCreate,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    ab = await crud.add_ability(db, ch_id, body.model_dump())
    return {"id": ab.id}


@router.delete("/characters/{ch_id}/abilities/{ability_id}")
async def delete_ability(
    ch_id: int,
    ability_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    ok = await crud.delete_ability(db, ability_id)
    if not ok:
        raise HTTPException(404, "Ability not found")
    return {"status": "deleted"}


# =========================
# STATES
# =========================

@router.get("/characters/{ch_id}/states")
async def list_states(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    states = await crud.list_states(db, ch_id)
    return [
        {
            "id": s.id,
            "name": s.name,
            "hp_cost": s.hp_cost,
            "duration": s.duration,
            "is_active": s.is_active,
        }
        for s in states
    ]


@router.post("/characters/{ch_id}/states")
async def add_state(
    ch_id: int,
    body: schemas.StateCreate,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    st = await crud.add_state(db, ch_id, body.model_dump())
    return {"id": st.id}


@router.delete("/characters/{ch_id}/states/{state_id}")
async def delete_state(
    ch_id: int,
    state_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    ok = await crud.delete_state(db, state_id)
    if not ok:
        raise HTTPException(404, "State not found")
    return {"status": "deleted"}


# =========================
# EQUIPMENT
# =========================

@router.get("/characters/{ch_id}/equipment")
async def get_equipment(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    eq = await crud.get_or_create_equipment(db, ch_id)
    return {
        "head": eq.head,
        "armor": eq.armor,
        "back": eq.back,
        "hands": eq.hands,
        "legs": eq.legs,
        "feet": eq.feet,
        "weapon1": eq.weapon1,
        "weapon2": eq.weapon2,
        "belt": eq.belt,
        "ring1": eq.ring1,
        "ring2": eq.ring2,
        "ring3": eq.ring3,
        "ring4": eq.ring4,
        "jewelry": eq.jewelry,
    }


@router.patch("/characters/{ch_id}/equipment")
async def update_equipment(
    ch_id: int,
    body: schemas.EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    tg_user = _auth_user(x_tg_init_data)
    u = await crud.get_or_create_user(db, tg_id=int(tg_user["id"]))

    ch = await crud.get_character_by_id(db, ch_id)
    if not ch:
        raise HTTPException(404, "Character not found")

    is_dm = int(tg_user["id"]) in settings.dm_ids()
    if ch.owner_user_id != u.id and not is_dm:
        raise HTTPException(403, "No access")

    eq = await crud.update_equipment(db, ch_id, body.model_dump(exclude_unset=True))
    return {"status": "ok", "equipment": {"id": eq.id}}


# =========================
# FULL SHEET (one call for webapp)
# =========================

@router.get("/characters/{ch_id}/sheet")
async def get_full_sheet(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-TG-INIT-DATA"),
):
    """Удобно для WebApp: одним запросом тянем всё."""
    _ = _auth_user(x_tg_init_data)
    # проверку доступа делаем через list_items (там уже владелец/DM)
    ch = await get_character(ch_id, db=db, x_tg_init_data=x_tg_init_data)
    items = await list_items(ch_id, db=db, x_tg_init_data=x_tg_init_data)
    spells = await list_spells(ch_id, db=db, x_tg_init_data=x_tg_init_data)
    abilities = await list_abilities(ch_id, db=db, x_tg_init_data=x_tg_init_data)
    states = await list_states(ch_id, db=db, x_tg_init_data=x_tg_init_data)
    equipment = await get_equipment(ch_id, db=db, x_tg_init_data=x_tg_init_data)

    return {
        "character": ch,
        "items": items,
        "spells": spells,
        "abilities": abilities,
        "states": states,
        "equipment": equipment,
    }

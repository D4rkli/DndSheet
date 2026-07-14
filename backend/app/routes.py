import asyncio
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from .db import get_db
from .deps import get_current_user, get_owned_or_dm_character, resolve_auth_profile
from .models import Character, User
from .config import settings
from . import crud, schemas

router = APIRouter()


@router.get("/me")
async def me(
    u: User = Depends(get_current_user),
    profile: dict = Depends(resolve_auth_profile),
):
    return {
        "provider": profile.get("provider"),
        "tg_id": u.tg_id,
        "vk_id": u.vk_id,
        "username": profile.get("username"),
        "first_name": profile.get("first_name"),
        "last_name": profile.get("last_name"),
        "photo_url": profile.get("photo_url"),
        "display_name": profile.get("first_name") or profile.get("username") or "Аккаунт",
        "user_id": u.id,
        "is_dm": u.tg_id in settings.dm_ids(),
        "is_dev": u.tg_id in settings.dev_ids(),
    }


@router.post("/feedback")
async def send_feedback(
    body: schemas.FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
    profile: dict = Depends(resolve_auth_profile),
):
    kind = body.kind if body.kind in ("bug", "suggestion") else "suggestion"
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Text is required")

    await crud.create_feedback_report(db, u.id, kind, text)

    display_name = profile.get("first_name") or profile.get("username") or f"Пользователь #{u.id}"
    emoji = "🐛" if kind == "bug" else "💡"
    label = "Баг" if kind == "bug" else "Предложение"
    message = f"{emoji} {label} от {display_name}: {text[:1000]}"

    async def _notify(dev_tg_id: int) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
                    json={"chat_id": dev_tg_id, "text": message},
                )
                if resp.status_code != 200:
                    return {"tg_id": dev_tg_id, "ok": False, "error": resp.text[:300]}
                return {"tg_id": dev_tg_id, "ok": True}
        except Exception as e:
            print("FEEDBACK NOTIFY ERROR:", repr(e))
            return {"tg_id": dev_tg_id, "ok": False, "error": repr(e)}

    dev_ids = list(settings.dev_ids())
    # best-effort, in parallel — a slow/unreachable Telegram API shouldn't make
    # the whole request wait on each dev sequentially (the report is already saved).
    # Surface per-recipient results back to the caller so a broken DEV_USER_IDS /
    # BOT_TOKEN / "user never started the bot" setup is diagnosable from the app
    # itself, without needing server access.
    notify_results = await asyncio.gather(*(_notify(dev_tg_id) for dev_tg_id in dev_ids))

    return {"status": "ok", "notify_results": notify_results}


@router.get("/characters")
async def list_characters(
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    chars = await crud.list_characters(db, u.id)

    return [
        {
            "id": c.id,
            "name": c.name,
            "race": c.race,
            "klass": c.klass,
            "level": c.level,
            "is_own": is_own,
            "owner_name": None if is_own else (c.owner.first_name or (f"@{c.owner.username}" if c.owner.username else f"Игрок #{c.owner.id}")),
        }
        for c, is_own in chars
    ]


@router.get("/characters/{ch_id}")
async def get_character(
    ch: Character = Depends(get_owned_or_dm_character),
):

    # отдаём расширенный лист (чтобы webapp мог рисовать все поля)
    return {
        "id": ch.id,
        "name": ch.name,
        "race": ch.race,
        "gender": ch.gender,
        "klass": ch.klass,
        "level": ch.level,
        "xp": ch.xp,
        "xp_per_level": ch.xp_per_level,

        "gold": getattr(ch, "gold", 0),
        "silver": getattr(ch, "silver", 0),
        "copper": getattr(ch, "copper", 0),

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
        "aggression": ch.aggression,
        "kindness": ch.kindness,
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

@router.patch("/characters/{ch_id}")
async def update_character(
    body: schemas.CharacterUpdate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
    ch: Character = Depends(get_owned_or_dm_character),
):

    ch = await crud.update_character(db, ch, u.id, body)
    return ch

@router.post("/characters")
async def create_character(
    body: schemas.CharacterCreate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    ch = await crud.create_character(db, u.id, body.name)
    return {"id": ch.id, "name": ch.name}


@router.delete("/characters/{ch_id}")
async def delete_character(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    ok = await crud.delete_character(db, u.id, ch_id)
    if not ok:
        raise HTTPException(404, "Character not found")
    return {"status": "ok"}


@router.post("/characters/{ch_id}/items")
async def add_item(
    ch_id: int,
    body: schemas.ItemCreate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    it = await crud.add_item(db, ch_id, body.name, body.description, body.stats, body.qty)
    return {"id": it.id, "name": it.name, "description": it.description, "stats": it.stats, "qty": it.qty}

@router.get("/characters/{ch_id}/items")
async def list_items(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    items = await crud.list_items(db, ch_id)

    return [
        {
            "id": i.id,
            "name": i.name,
            "description": i.description,
            "stats": i.stats,
            "qty": i.qty,
        }
        for i in items
    ]

@router.delete("/characters/{ch_id}/items/{item_id}")
async def delete_item(
    ch_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    ok = await crud.delete_item(db, item_id)
    if not ok:
        raise HTTPException(404, "Item not found")

    return {"status": "deleted"}

@router.patch("/characters/{ch_id}/items/{item_id}")
async def patch_item(
    ch_id: int,
    item_id: int,
    data: schemas.ItemUpdate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    obj = await crud.update_item(db, ch_id, item_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"id": obj.id, "name": obj.name, "description": obj.description, "stats": obj.stats, "qty": obj.qty}



# =========================
# SPELLS
# =========================

@router.get("/characters/{ch_id}/spells")
async def list_spells(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    spells = await crud.list_spells(db, ch_id)
    return [
        {
            "id": s.id,
            "name": s.name,
            "level": s.level,
            "description": s.description,
            "range": s.range,
            "duration": s.duration,
            "cost": s.cost,
            "ap_cost": s.ap_cost,
        }
        for s in spells
    ]


@router.post("/characters/{ch_id}/spells")
async def add_spell(
    ch_id: int,
    body: schemas.SpellCreate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    sp = await crud.add_spell(db, ch_id, body.model_dump())
    return {"id": sp.id}


@router.delete("/characters/{ch_id}/spells/{spell_id}")
async def delete_spell(
    ch_id: int,
    spell_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
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
    ch: Character = Depends(get_owned_or_dm_character),
):
    abilities = await crud.list_abilities(db, ch_id)
    return [
        {
            "id": a.id,
            "name": a.name,
            "level": a.level,
            "description": a.description,
            "range": a.range,
            "duration": a.duration,
            "cost": a.cost,
            "ap_cost": a.ap_cost,
        }
        for a in abilities
    ]


@router.post("/characters/{ch_id}/abilities")
async def add_ability(
    ch_id: int,
    body: schemas.AbilityCreate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    ab = await crud.add_ability(db, ch_id, body.model_dump())
    return {"id": ab.id}


@router.delete("/characters/{ch_id}/abilities/{ability_id}")
async def delete_ability(
    ch_id: int,
    ability_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
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
    ch: Character = Depends(get_owned_or_dm_character),
):
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

@router.patch("/characters/{ch_id}/spells/{spell_id}")
async def patch_spell(
    ch_id: int,
    spell_id: int,
    data: schemas.SpellUpdate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    obj = await crud.update_spell(db, ch_id, spell_id, data)
    if not obj:
        raise HTTPException(404, "Spell not found")

    return {"id": obj.id, "name": obj.name, "level": obj.level, "description": obj.description, "range": obj.range, "duration": obj.duration, "cost": obj.cost, "ap_cost": obj.ap_cost}


@router.patch("/characters/{ch_id}/abilities/{ability_id}")
async def patch_ability(
    ch_id: int,
    ability_id: int,
    data: schemas.AbilityUpdate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    obj = await crud.update_ability(db, ch_id, ability_id, data)
    if not obj:
        raise HTTPException(404, "Ability not found")

    return {"id": obj.id, "name": obj.name, "level": obj.level, "description": obj.description, "range": obj.range, "duration": obj.duration, "cost": obj.cost, "ap_cost": obj.ap_cost}


@router.patch("/characters/{ch_id}/states/{state_id}")
async def patch_state(
    ch_id: int,
    state_id: int,
    data: schemas.StateUpdate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    obj = await crud.update_state(db, ch_id, state_id, data)
    if not obj:
        raise HTTPException(404, "State not found")

    return {"id": obj.id, "name": obj.name, "hp_cost": obj.hp_cost, "duration": obj.duration, "is_active": obj.is_active}


@router.post("/characters/{ch_id}/states")
async def add_state(
    ch_id: int,
    body: schemas.StateCreate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    st = await crud.add_state(db, ch_id, body.model_dump())
    return {"id": st.id}


@router.delete("/characters/{ch_id}/states/{state_id}")
async def delete_state(
    ch_id: int,
    state_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
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
    ch: Character = Depends(get_owned_or_dm_character),
):
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
    ch: Character = Depends(get_owned_or_dm_character),
):
    eq = await crud.update_equipment(db, ch_id, body.model_dump(exclude_unset=True))
    return {"status": "ok", "equipment": {"id": eq.id}}

# =========================
# SUMMONS
# =========================

@router.get("/characters/{ch_id}/summons")
async def list_summons(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    rows = await crud.list_summons(db, ch_id)
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "duration": s.duration,
            "hp_ratio": s.hp_ratio,
            "attack_ratio": s.attack_ratio,
            "defense_ratio": s.defense_ratio,
            "count": s.count,
        }
        for s in rows
    ]


@router.post("/characters/{ch_id}/summons")
async def add_summon(
    ch_id: int,
    body: schemas.SummonCreate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    obj = await crud.add_summon(db, ch_id, body.model_dump())
    return {"id": obj.id}


@router.patch("/characters/{ch_id}/summons/{summon_id}")
async def patch_summon(
    ch_id: int,
    summon_id: int,
    body: schemas.SummonUpdate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    obj = await crud.update_summon(db, ch_id, summon_id, body)
    if not obj:
        raise HTTPException(404, "Summon not found")
    return {"status": "ok"}


@router.delete("/characters/{ch_id}/summons/{summon_id}")
async def delete_summon(
    ch_id: int,
    summon_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    ok = await crud.delete_summon(db, summon_id)
    if not ok:
        raise HTTPException(404, "Summon not found")
    return {"status": "deleted"}

# =========================
# ACTION LOG (persistent combat history)
# =========================

@router.get("/characters/{ch_id}/log")
async def list_action_log(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    entries = await crud.list_action_log(db, ch_id)
    return [
        {"id": e.id, "text": e.text, "created_at": e.created_at.isoformat()}
        for e in entries
    ]


@router.post("/characters/{ch_id}/log")
async def add_action_log(
    ch_id: int,
    body: schemas.ActionLogCreate,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    entry = await crud.add_action_log(db, ch_id, body.text)
    return {"id": entry.id, "text": entry.text, "created_at": entry.created_at.isoformat()}


@router.delete("/characters/{ch_id}/log")
async def clear_action_log(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    await crud.clear_action_log(db, ch_id)
    return {"status": "ok"}

# =========================
# FULL SHEET (one call for webapp)
# =========================

@router.get("/characters/{ch_id}/sheet")
async def get_full_sheet(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    ch: Character = Depends(get_owned_or_dm_character),
):
    """For WebApp: one request returns everything, including template + custom values."""
    sheet = await crud.get_sheet(db, ch_id, ch.owner_user_id)
    if not sheet:
        raise HTTPException(404, "Character not found")

    # serialize ORM objects
    character = sheet["character"]
    equipment = sheet["equipment"]

    return {
        "character": {
            "id": character.id,
            "name": character.name,
            "race": character.race,
            "gender": character.gender,
            "klass": character.klass,
            "level": character.level,
            "xp": character.xp,
            "xp_per_level": character.xp_per_level,
            "gold": getattr(character, "gold", 0),
            "silver": getattr(character, "silver", 0),
            "copper": getattr(character, "copper", 0),
            "hp": character.hp,
            "mana": character.mana,
            "energy": character.energy,
            "hp_max": character.hp_max,
            "mana_max": character.mana_max,
            "energy_max": character.energy_max,
            "hp_per_level": character.hp_per_level,
            "mana_per_level": character.mana_per_level,
            "energy_per_level": character.energy_per_level,
            "aggression": character.aggression,
            "kindness": character.kindness,
            "intellect": character.intellect,
            "confidence": character.confidence,
            "fearlessness": character.fearlessness,
            "humor": character.humor,
            "emotionality": character.emotionality,
            "sociability": character.sociability,
            "responsibility": character.responsibility,
            "intimidation": character.intimidation,
            "attentiveness": character.attentiveness,
            "learnability": character.learnability,
            "luck": character.luck,
            "stealth": character.stealth,
            "initiative": character.initiative,
            "attack": character.attack,
            "counterattack": character.counterattack,
            "steps": character.steps,
            "defense": character.defense,
            "perm_armor": character.perm_armor,
            "temp_armor": character.temp_armor,
            "action_points": character.action_points,
            "dodges": character.dodges,
            "level_up_rules": character.level_up_rules,
            "template_id": character.template_id,
            "campaign_id": character.campaign_id,
        },
        "items": [
            {
                "id": i.id,
                "name": i.name,
                "description": i.description,
                "stats": i.stats,
                "qty": i.qty,   # ← ОБЯЗАТЕЛЬНО
            }
            for i in sheet["items"]
        ],
        "spells": [
            {
                "id": s.id,
                "name": s.name,
                "level": s.level,
                "description": s.description,
                "range": s.range,
                "duration": s.duration,
                "cost": s.cost,
                "ap_cost": s.ap_cost,
            }
            for s in sheet["spells"]
        ],
        "abilities": [
            {
                "id": a.id,
                "name": a.name,
                "level": a.level,
                "description": a.description,
                "range": a.range,
                "duration": a.duration,
                "cost": a.cost,
                "ap_cost": a.ap_cost,
            }
            for a in sheet["abilities"]
        ],
        "states": [
            {"id": st.id, "name": st.name, "hp_cost": st.hp_cost, "duration": st.duration, "is_active": st.is_active}
            for st in sheet["states"]
        ],
        "equipment": {
            "head": equipment.head,
            "armor": equipment.armor,
            "back": equipment.back,
            "hands": equipment.hands,
            "legs": equipment.legs,
            "feet": equipment.feet,
            "weapon1": equipment.weapon1,
            "weapon2": equipment.weapon2,
            "belt": equipment.belt,
            "ring1": equipment.ring1,
            "ring2": equipment.ring2,
            "ring3": equipment.ring3,
            "ring4": equipment.ring4,
            "jewelry": equipment.jewelry,
        },
        "summons": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "duration": s.duration,
                "hp_ratio": s.hp_ratio,
                "attack_ratio": s.attack_ratio,
                "defense_ratio": s.defense_ratio,
                "count": s.count,
                "mana_ratio": s.mana_ratio,
                "energy_ratio": s.energy_ratio,
                "initiative_ratio": s.initiative_ratio,
                "luck_ratio": s.luck_ratio,
                "steps_ratio": s.steps_ratio,
                "attack_range_ratio": s.attack_range_ratio,
            }
            for s in sheet.get("summons", [])
        ],
        "template": sheet.get("template"),
        "custom_values": sheet.get("custom_values", {}),
    }


# =========================
# EXPORT / IMPORT
# =========================

@router.get("/characters/{ch_id}/export")
async def export_character_sheet(
    ch_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    data = await crud.export_sheet(db, ch_id, u.id)
    if not data:
        raise HTTPException(404, "Character not found")
    return data


@router.post("/characters/import")
async def import_character_sheet(
    body: schemas.SheetImportIn,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    ch = await crud.import_sheet(db, u.id, body.model_dump())
    return {"status": "ok", "character_id": ch.id}


# =========================
# TEMPLATES
# =========================

@router.get("/templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    templates = await crud.list_templates(db, u.id)
    return [
        {
            "id": t.id,
            "name": t.name,
            "config": json.loads(t.config_json or "{}"),
        }
        for t in templates
    ]


@router.post("/templates")
async def create_template(
    body: schemas.SheetTemplateCreate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    t = await crud.create_template(db, u.id, body.name, body.config)
    return {"status": "ok", "template_id": t.id}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    ok = await crud.delete_template(db, u.id, template_id)
    if not ok:
        raise HTTPException(404, "Template not found")
    return {"status": "ok"}


@router.post("/templates/{template_id}/create-character")
async def create_character_from_template(
    template_id: int,
    body: schemas.CharacterCreate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    ch = await crud.create_character_from_template(db, u.id, template_id, body.name)
    if not ch:
        raise HTTPException(404, "Template not found")
    return {"status": "ok", "character_id": ch.id}


# =========================
# TEMPLATE APPLY + CUSTOM VALUES
# =========================

@router.post("/characters/{ch_id}/apply-template")
async def apply_template(
    ch_id: int,
    body: schemas.ApplyTemplate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    ch = await crud.get_character_for_user(db, ch_id, u.id)
    if not ch:
        raise HTTPException(404, "Character not found")

    updated = await crud.apply_template_to_character(db, ch_id, u.id, body.template_id)
    if not updated:
        raise HTTPException(404, "Template not found")

    return {"status": "ok", "character_id": updated.id, "template_id": updated.template_id}


@router.patch("/characters/{ch_id}/custom")
async def patch_custom_values(
    ch_id: int,
    body: schemas.CustomValuesUpdate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):

    ch = await crud.get_character_for_user(db, ch_id, u.id)
    if not ch:
        raise HTTPException(404, "Character not found")

    ok = await crud.update_custom_values(db, ch_id, u.id, body.values)
    if not ok:
        raise HTTPException(404, "Character not found")

    return {"status": "ok"}

from sqlalchemy import select
from .schemas import CharacterUpdate
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    User,
    Character,
    Item,
    Spell,
    Ability,
    State,
)

# =========================
# USERS
# =========================

async def get_or_create_user(db: AsyncSession, tg_id: int) -> User:
    q = await db.execute(
        select(User).where(User.tg_id == tg_id)
    )
    user = q.scalar_one_or_none()

    if user:
        return user

    user = User(tg_id=tg_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# =========================
# CHARACTERS
# =========================

async def list_characters(
    db: AsyncSession,
    user_id: int,
) -> list[Character]:
    q = await db.execute(
        select(Character).where(
            Character.owner_user_id == user_id
        )
    )
    return list(q.scalars().all())

async def create_character(db: AsyncSession, user_id: int, name: str) -> Character:
    ch = Character(
        owner_user_id=user_id,
        name=name,
        level=1,

        hp=10, hp_max=10, hp_per_level=0,
        mana=5, mana_max=5, mana_per_level=0,
        energy=3, energy_max=3, energy_per_level=0,
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return ch

async def get_character_for_user(
    db: AsyncSession,
    character_id: int,
    user_id: int,
) -> Character | None:
    q = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.owner_user_id == user_id,
        )
    )
    return q.scalar_one_or_none()


async def get_character_by_id(
    db: AsyncSession,
    character_id: int,
) -> Character | None:
    q = await db.execute(
        select(Character).where(
            Character.id == character_id
        )
    )
    return q.scalar_one_or_none()


async def update_character(
    db: AsyncSession,
    character_id: int,
    user_id: int,
    data: CharacterUpdate,
):
    ch = await get_character_for_user(db, character_id, user_id)
    if not ch:
        return None

    payload = data.model_dump(exclude_unset=True)

    # Level: minimum 1
    if "level" in payload:
        payload["level"] = max(1, int(payload["level"]))

    # Clamp max resources to >=0
    for field in ("hp_max", "mana_max", "energy_max"):
        if field in payload:
            payload[field] = max(0, int(payload[field]))

    # Per-level deltas: ints
    for field in ("hp_per_level", "mana_per_level", "energy_per_level"):
        if field in payload:
            payload[field] = int(payload[field])

    # Apply any known fields directly
    for key, value in payload.items():
        if not hasattr(ch, key):
            continue
        # keep strings as-is, cast ints where appropriate
        if isinstance(value, bool):
            setattr(ch, key, value)
        elif isinstance(value, int):
            setattr(ch, key, value)
        elif value is None:
            setattr(ch, key, value)
        else:
            # pydantic may give str for some fields
            setattr(ch, key, value)

    # Clamp current resources
    for res in ("hp", "mana", "energy"):
        cur = getattr(ch, res, 0) or 0
        cur = max(0, int(cur))
        max_value = getattr(ch, f"{res}_max", 0) or 0
        if max_value > 0:
            cur = min(cur, max_value)
        setattr(ch, res, cur)

    await db.commit()
    await db.refresh(ch)
    return ch

# =========================
# ITEMS (INVENTORY)
# =========================

async def list_items(
    db: AsyncSession,
    character_id: int,
) -> list[Item]:
    q = await db.execute(
        select(Item).where(
            Item.character_id == character_id
        )
    )
    return list(q.scalars().all())


async def add_item(
    db: AsyncSession,
    character_id: int,
    name: str,
    description: str,
    stats: str | None = None,
) -> Item:
    it = Item(
        character_id=character_id,
        name=name,
        description=description,
        stats=stats,
    )
    db.add(it)
    await db.commit()
    await db.refresh(it)
    return it


async def delete_item(
    db: AsyncSession,
    item_id: int,
) -> bool:
    q = await db.execute(
        select(Item).where(Item.id == item_id)
    )
    item = q.scalar_one_or_none()

    if not item:
        return False

    await db.delete(item)
    await db.commit()
    return True


# =========================
# SPELLS
# =========================

async def add_spell(
    db: AsyncSession,
    character_id: int,
    payload: dict,
) -> Spell:
    sp = Spell(
        character_id=character_id,
        **payload,
    )
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp


# =========================
# ABILITIES
# =========================

async def add_ability(
    db: AsyncSession,
    character_id: int,
    payload: dict,
) -> Ability:
    ab = Ability(
        character_id=character_id,
        **payload,
    )
    db.add(ab)
    await db.commit()
    await db.refresh(ab)
    return ab


# =========================
# STATES
# =========================

async def add_state(
    db: AsyncSession,
    character_id: int,
    payload: dict,
) -> State:
    st = State(
        character_id=character_id,
        **payload,
    )
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st


# =========================
# EQUIPMENT
# =========================

async def get_or_create_equipment(db: AsyncSession, character_id: int) -> Equipment:
    q = await db.execute(select(Equipment).where(Equipment.character_id == character_id))
    eq = q.scalar_one_or_none()
    if eq:
        return eq
    eq = Equipment(character_id=character_id)
    db.add(eq)
    await db.commit()
    await db.refresh(eq)
    return eq


async def update_equipment(db: AsyncSession, character_id: int, payload: dict) -> Equipment:
    eq = await get_or_create_equipment(db, character_id)
    for key, value in payload.items():
        if hasattr(eq, key) and value is not None:
            setattr(eq, key, str(value))
    await db.commit()
    await db.refresh(eq)
    return eq


# =========================
# SPELLS / ABILITIES / STATES
# =========================

async def list_spells(db: AsyncSession, character_id: int) -> list[Spell]:
    q = await db.execute(select(Spell).where(Spell.character_id == character_id))
    return list(q.scalars().all())


async def delete_spell(db: AsyncSession, spell_id: int) -> bool:
    q = await db.execute(select(Spell).where(Spell.id == spell_id))
    sp = q.scalar_one_or_none()
    if not sp:
        return False
    await db.delete(sp)
    await db.commit()
    return True


async def list_abilities(db: AsyncSession, character_id: int) -> list[Ability]:
    q = await db.execute(select(Ability).where(Ability.character_id == character_id))
    return list(q.scalars().all())


async def delete_ability(db: AsyncSession, ability_id: int) -> bool:
    q = await db.execute(select(Ability).where(Ability.id == ability_id))
    ab = q.scalar_one_or_none()
    if not ab:
        return False
    await db.delete(ab)
    await db.commit()
    return True


async def list_states(db: AsyncSession, character_id: int) -> list[State]:
    q = await db.execute(select(State).where(State.character_id == character_id))
    return list(q.scalars().all())


async def delete_state(db: AsyncSession, state_id: int) -> bool:
    q = await db.execute(select(State).where(State.id == state_id))
    st = q.scalar_one_or_none()
    if not st:
        return False
    await db.delete(st)
    await db.commit()
    return True


# =========================
# TEMPLATES
# =========================

async def list_templates(db: AsyncSession, user_id: int) -> list[SheetTemplate]:
    q = await db.execute(select(SheetTemplate).where(SheetTemplate.owner_user_id == user_id))
    return list(q.scalars().all())


async def create_template(db: AsyncSession, user_id: int, name: str, config: dict) -> SheetTemplate:
    tpl = SheetTemplate(owner_user_id=user_id, name=name, config_json=json.dumps(config, ensure_ascii=False))
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def delete_template(db: AsyncSession, user_id: int, template_id: int) -> bool:
    q = await db.execute(select(SheetTemplate).where(SheetTemplate.id == template_id, SheetTemplate.owner_user_id == user_id))
    tpl = q.scalar_one_or_none()
    if not tpl:
        return False
    await db.delete(tpl)
    await db.commit()
    return True


def _tpl_defaults(config: dict) -> dict:
    defaults: dict = {}
    for sec in config.get("custom_sections", []) or []:
        for field in sec.get("fields", []) or []:
            key = str(field.get("key", "")).strip()
            if not key:
                continue
            if "default" in field:
                defaults[key] = field.get("default")
            else:
                defaults[key] = "" if field.get("type") in ("text", "textarea") else 0
    return defaults


async def apply_template_to_character(db: AsyncSession, character_id: int, user_id: int, template_id: int) -> Character | None:
    ch = await get_character_for_user(db, character_id, user_id)
    if not ch:
        return None

    q = await db.execute(select(SheetTemplate).where(SheetTemplate.id == template_id, SheetTemplate.owner_user_id == user_id))
    tpl = q.scalar_one_or_none()
    if not tpl:
        return None

    try:
        config = json.loads(tpl.config_json or "{}")
    except Exception:
        config = {}

    try:
        cur = json.loads(ch.custom_values or "{}")
        if not isinstance(cur, dict):
            cur = {}
    except Exception:
        cur = {}

    for k, v in _tpl_defaults(config).items():
        cur.setdefault(k, v)

    ch.template_id = tpl.id
    ch.custom_values = json.dumps(cur, ensure_ascii=False)

    await db.commit()
    await db.refresh(ch)
    return ch


async def update_custom_values(db: AsyncSession, character_id: int, user_id: int, values: dict) -> bool:
    ch = await get_character_for_user(db, character_id, user_id)
    if not ch:
        return False
    try:
        cur = json.loads(ch.custom_values or "{}")
        if not isinstance(cur, dict):
            cur = {}
    except Exception:
        cur = {}

    for k, v in (values or {}).items():
        cur[str(k)] = v

    ch.custom_values = json.dumps(cur, ensure_ascii=False)
    await db.commit()
    return True


# =========================
# SHEET (one-call)
# =========================

async def get_sheet(db: AsyncSession, character_id: int, user_id: int) -> dict | None:
    ch = await get_character_for_user(db, character_id, user_id)
    if not ch:
        return None

    items = await list_items(db, character_id)
    spells = await list_spells(db, character_id)
    abilities = await list_abilities(db, character_id)
    states = await list_states(db, character_id)
    eq = await get_or_create_equipment(db, character_id)

    tpl = None
    config = None
    if ch.template_id:
        q = await db.execute(select(SheetTemplate).where(SheetTemplate.id == ch.template_id))
        tpl = q.scalar_one_or_none()
        if tpl:
            try:
                config = json.loads(tpl.config_json or "{}")
            except Exception:
                config = {}

    try:
        custom = json.loads(ch.custom_values or "{}")
        if not isinstance(custom, dict):
            custom = {}
    except Exception:
        custom = {}

    return {
        "character": ch,
        "items": items,
        "spells": spells,
        "abilities": abilities,
        "states": states,
        "equipment": eq,
        "template": {"id": tpl.id, "name": tpl.name, "config": config} if tpl else None,
        "custom_values": custom,
    }


# =========================
# IMPORT / EXPORT
# =========================

async def export_character(db: AsyncSession, character_id: int, user_id: int) -> dict | None:
    sheet = await get_sheet(db, character_id, user_id)
    if not sheet:
        return None

    ch = sheet["character"]
    data = {
        "character": {
            "name": ch.name,
            "race": ch.race,
            "gender": ch.gender,
            "klass": ch.klass,
            "level": ch.level,
            "xp": ch.xp,

            "hp": ch.hp,
            "mana": ch.mana,
            "energy": ch.energy,
            "hp_max": ch.hp_max,
            "mana_max": ch.mana_max,
            "energy_max": ch.energy_max,
            "hp_per_level": ch.hp_per_level,
            "mana_per_level": ch.mana_per_level,
            "energy_per_level": ch.energy_per_level,

            # include all numeric stats present on model
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
        },
        "items": [
            {"name": i.name, "description": i.description, "stats": i.stats}
            for i in sheet["items"]
        ],
        "spells": [
            {"name": s.name, "description": s.description, "range": s.range, "duration": s.duration, "cost": s.cost}
            for s in sheet["spells"]
        ],
        "abilities": [
            {"name": a.name, "description": a.description, "range": a.range, "duration": a.duration, "cost": a.cost}
            for a in sheet["abilities"]
        ],
        "states": [
            {"name": st.name, "hp_cost": st.hp_cost, "duration": st.duration, "is_active": st.is_active}
            for st in sheet["states"]
        ],
        "equipment": {
            "head": sheet["equipment"].head,
            "armor": sheet["equipment"].armor,
            "back": sheet["equipment"].back,
            "hands": sheet["equipment"].hands,
            "legs": sheet["equipment"].legs,
            "feet": sheet["equipment"].feet,
            "weapon1": sheet["equipment"].weapon1,
            "weapon2": sheet["equipment"].weapon2,
            "belt": sheet["equipment"].belt,
            "ring1": sheet["equipment"].ring1,
            "ring2": sheet["equipment"].ring2,
            "ring3": sheet["equipment"].ring3,
            "ring4": sheet["equipment"].ring4,
            "jewelry": sheet["equipment"].jewelry,
        },
        "custom_values": sheet["custom_values"],
    }

    if sheet["template"]:
        data["template"] = sheet["template"]

    return data


async def import_character(db: AsyncSession, user_id: int, payload: dict) -> Character:
    template_id = None

    tpl = payload.get("template")
    if isinstance(tpl, dict) and tpl.get("config"):
        name = str(tpl.get("name") or "Template")
        tpl_obj = await create_template(db, user_id, name=name, config=tpl.get("config") or {})
        template_id = tpl_obj.id

    ch_data = payload.get("character") or {}
    name = str(ch_data.get("name") or "Character")
    ch = await create_character(db, user_id, name)

    # set fields on character
    for key, value in ch_data.items():
        if hasattr(ch, key) and value is not None:
            setattr(ch, key, value)

    # set template + custom values
    if template_id:
        ch.template_id = template_id

    if isinstance(payload.get("custom_values"), dict):
        ch.custom_values = json.dumps(payload.get("custom_values"), ensure_ascii=False)

    await db.commit()
    await db.refresh(ch)

    # equipment
    if isinstance(payload.get("equipment"), dict):
        await update_equipment(db, ch.id, payload.get("equipment") or {})

    # items
    for i in payload.get("items") or []:
        if isinstance(i, dict) and i.get("name"):
            await add_item(db, ch.id, i.get("name"), i.get("description", ""), i.get("stats", ""))

    # spells
    for s in payload.get("spells") or []:
        if isinstance(s, dict) and s.get("name"):
            await add_spell(db, ch.id, {
                "name": s.get("name"),
                "description": s.get("description", ""),
                "range": s.get("range", ""),
                "duration": s.get("duration", ""),
                "cost": s.get("cost", ""),
            })

    for a in payload.get("abilities") or []:
        if isinstance(a, dict) and a.get("name"):
            await add_ability(db, ch.id, {
                "name": a.get("name"),
                "description": a.get("description", ""),
                "range": a.get("range", ""),
                "duration": a.get("duration", ""),
                "cost": a.get("cost", ""),
            })

    for st in payload.get("states") or []:
        if isinstance(st, dict) and st.get("name"):
            await add_state(db, ch.id, {
                "name": st.get("name"),
                "hp_cost": int(st.get("hp_cost", 0) or 0),
                "duration": st.get("duration", ""),
                "is_active": bool(st.get("is_active", True)),
            })

    return ch


# Backward-compatible aliases

async def export_sheet(db: AsyncSession, character_id: int, user_id: int) -> dict | None:
    return await export_character(db, character_id, user_id)


async def import_sheet(db: AsyncSession, user_id: int, payload: dict) -> Character:
    return await import_character(db, user_id, payload)

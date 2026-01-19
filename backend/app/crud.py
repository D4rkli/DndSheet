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
    Equipment,
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

    # текстовые
    for field in ("name", "race", "gender", "klass", "level_up_rules"):
        if field in payload:
            setattr(ch, field, payload[field])

    # опыт
    if "xp" in payload:
        ch.xp = max(0, int(payload["xp"]))

    # уровень (минимум 1)
    if "level" in payload:
        ch.level = max(1, int(payload["level"]))

    # характер / прочие числовые параметры
    int_fields = (
        "aggression_kindness",
        "intellect",
        "fearlessness",
        "humor",
        "emotionality",
        "sociability",
        "responsibility",
        "intimidation",
        "attentiveness",
        "learnability",
        "luck",
        "stealth",

        "initiative",
        "attack",
        "counterattack",
        "steps",
        "defense",
        "perm_armor",
        "temp_armor",
        "action_points",
        "dodges",
    )

    for field in int_fields:
        if field in payload:
            setattr(ch, field, int(payload[field]))

    # max значения (не меньше 0)
    for field in ("hp_max", "mana_max", "energy_max"):
        if field in payload:
            setattr(ch, field, max(0, int(payload[field])))

    # прибавка за уровень (может быть 0)
    for field in ("hp_per_level", "mana_per_level", "energy_per_level"):
        if field in payload:
            setattr(ch, field, int(payload[field]))

    # текущие ресурсы (не меньше 0, не больше max если max задан)
    for res in ("hp", "mana", "energy"):
        if res not in payload:
            continue

        value = max(0, int(payload[res]))
        max_value = getattr(ch, f"{res}_max", 0)

        if max_value and max_value > 0:
            value = min(value, max_value)

        setattr(ch, res, value)

    # если max уменьшили — подрежем текущее тоже
    for res in ("hp", "mana", "energy"):
        max_value = getattr(ch, f"{res}_max", 0)
        if max_value and max_value > 0:
            cur = getattr(ch, res, 0)
            if cur > max_value:
                setattr(ch, res, max_value)

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

    for field, value in payload.items():
        if hasattr(eq, field):
            setattr(eq, field, value or "")

    await db.commit()
    await db.refresh(eq)
    return eq

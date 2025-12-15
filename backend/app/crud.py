from sqlalchemy import select
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

async def create_character(
    db: AsyncSession,
    user_id: int,
    name: str,
) -> Character:
    ch = Character(
        owner_user_id=user_id,
        name=name,
        hp=10,
        mana=5,
        energy=3,
        level=1,
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
    data,
) -> Character | None:
    ch = await get_character_for_user(db, character_id, user_id)
    if not ch:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ch, field, value)

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

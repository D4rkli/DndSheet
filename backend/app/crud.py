import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, Character, Equipment, Item, Spell, Ability, State

async def get_or_create_user(db: AsyncSession, tg_id: int) -> User:
    q = await db.execute(select(User).where(User.tg_id == tg_id))
    user = q.scalar_one_or_none()
    if user:
        return user
    user = User(tg_id=tg_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def list_characters(db: AsyncSession, user_id: int) -> list[Character]:
    q = await db.execute(select(Character).where(Character.owner_user_id == user_id))
    return list(q.scalars().all())

async def get_character(
    db: AsyncSession,
    character_id: int,
    user_id: int,
):
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.owner_user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_character(db, character_id: int, user_id: int, data):
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == user_id
        )
    )
    ch = result.scalar_one_or_none()
    if not ch:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ch, field, value)

    await db.commit()
    await db.refresh(ch)
    return ch


async def get_character(db: AsyncSession, ch_id: int) -> Character | None:
    q = await db.execute(select(Character).where(Character.id == ch_id))
    return q.scalar_one_or_none()

async def add_item(db: AsyncSession, ch_id: int, name: str, description: str, stats: str) -> Item:
    it = Item(character_id=ch_id, name=name, description=description, stats=stats)
    db.add(it)
    await db.commit()
    await db.refresh(it)
    return it

async def add_spell(db: AsyncSession, ch_id: int, payload: dict) -> Spell:
    sp = Spell(character_id=ch_id, **payload)
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp

async def add_ability(db: AsyncSession, ch_id: int, payload: dict) -> Ability:
    ab = Ability(character_id=ch_id, **payload)
    db.add(ab)
    await db.commit()
    await db.refresh(ab)
    return ab

async def add_state(db: AsyncSession, ch_id: int, payload: dict) -> State:
    st = State(character_id=ch_id, **payload)
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st

import json
import secrets
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .schemas import CharacterUpdate
from .models import (
    User,
    Character,
    Item,
    Spell,
    Ability,
    State,
    Equipment,
    SheetTemplate,
    Summon,
    Campaign,
    CampaignMember,
    CampaignMessage,
)

# =========================
# INTERNAL HELPERS
# =========================

def _safe_json_dict(raw: str | None) -> dict:
    """Parse JSON string into dict; return {} on any error or non-dict."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# Fields used across CRUD updates (avoid copy-paste)
SPELL_FIELDS = ["name", "level", "description", "range", "duration", "cost"]
ABILITY_FIELDS = ["name", "level", "description", "range", "duration", "cost"]
STATE_FIELDS = ["name", "hp_cost", "duration", "is_active"]
ITEM_FIELDS = ["name", "description", "stats", "qty"]
SUMMON_FIELDS = [
    "name", "description", "duration",
    "hp_ratio", "attack_ratio", "defense_ratio",
    "mana_ratio", "energy_ratio",
    "initiative_ratio", "luck_ratio",
    "steps_ratio", "attack_range_ratio",
    "count",
]

# =========================
# USERS
# =========================

async def get_or_create_user(
    db: AsyncSession, tg_id: int, first_name: str | None = None, username: str | None = None
) -> User:
    q = await db.execute(select(User).where(User.tg_id == tg_id))
    user = q.scalar_one_or_none()
    if user:
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if username and user.username != username:
            user.username = username
        if db.is_modified(user):
            await db.commit()
            await db.refresh(user)
        return user

    user = User(tg_id=tg_id, first_name=first_name, username=username)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_or_create_user_by_vk(
    db: AsyncSession, vk_id: int, first_name: str | None = None, username: str | None = None
) -> User:
    q = await db.execute(select(User).where(User.vk_id == vk_id))
    user = q.scalar_one_or_none()
    if user:
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if username and user.username != username:
            user.username = username
        if db.is_modified(user):
            await db.commit()
            await db.refresh(user)
        return user

    user = User(vk_id=vk_id, first_name=first_name, username=username)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# =========================
# CHARACTERS
# =========================

async def list_characters(db: AsyncSession, user_id: int) -> list[tuple[Character, bool]]:
    """Own characters, plus (as a DM) characters from campaigns I run.

    Returns (character, is_own) pairs so the caller can tell them apart.
    """
    q = await db.execute(select(Character).where(Character.owner_user_id == user_id))
    own = [(c, True) for c in q.scalars().all()]

    q = await db.execute(
        select(Character)
        .join(Campaign, Campaign.id == Character.campaign_id)
        .where(Campaign.dm_user_id == user_id, Character.owner_user_id != user_id)
        .options(selectinload(Character.owner))
    )
    dm_visible = [(c, False) for c in q.scalars().all()]

    return own + dm_visible


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


async def get_character_for_user(db: AsyncSession, character_id: int, user_id: int) -> Character | None:
    q = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.owner_user_id == user_id,
        )
    )
    return q.scalar_one_or_none()


async def get_character_by_id(db: AsyncSession, character_id: int) -> Character | None:
    q = await db.execute(
        select(Character)
        .where(Character.id == character_id)
        .options(selectinload(Character.campaign))
    )
    return q.scalar_one_or_none()


async def update_character(
    db: AsyncSession,
    ch: Character,
    actor_user_id: int,
    data: CharacterUpdate,
):
    payload = data.model_dump(exclude_unset=True)

    # campaign_id needs a membership check, not a bare setattr — a character
    # can only be attached to a campaign its owner is DM of or a member of.
    # Only the owner may change it (not a DM editing someone else's sheet).
    if "campaign_id" in payload:
        campaign_id = payload.pop("campaign_id")
        if actor_user_id == ch.owner_user_id:
            if campaign_id is None:
                ch.campaign_id = None
            else:
                campaign = await get_campaign_by_id(db, campaign_id)
                is_member = campaign and (
                    campaign.dm_user_id == actor_user_id
                    or any(m.user_id == actor_user_id for m in campaign.members)
                )
                if is_member:
                    ch.campaign_id = campaign_id

    # Level: minimum 1
    if "level" in payload and payload["level"] is not None:
        payload["level"] = max(1, int(payload["level"]))

    # Clamp max resources to >=0
    for field in ("hp_max", "mana_max", "energy_max"):
        if field in payload and payload[field] is not None:
            payload[field] = max(0, int(payload[field]))

    for field in ("gold", "silver", "copper"):
        if field in payload and payload[field] is not None:
            payload[field] = max(0, int(payload[field]))

    # Per-level deltas: ints
    for field in ("hp_per_level", "mana_per_level", "energy_per_level", "xp_per_level"):
        if field in payload and payload[field] is not None:
            payload[field] = int(payload[field])

    # Apply fields
    for key, value in payload.items():
        if not hasattr(ch, key):
            continue
        setattr(ch, key, value)

    # Clamp current resources
    for res in ("hp", "mana", "energy"):
        cur = getattr(ch, res, 0) or 0
        cur = max(0, int(cur))
        max_value = getattr(ch, f"{res}_max", 0) or 0
        if max_value > 0:
            cur = min(cur, int(max_value))
        setattr(ch, res, cur)

    await db.commit()
    await db.refresh(ch)
    return ch


# =========================
# CAMPAIGNS
# =========================

async def create_campaign(db: AsyncSession, dm_user_id: int, name: str) -> Campaign:
    campaign = Campaign(
        name=name,
        dm_user_id=dm_user_id,
        invite_code=secrets.token_urlsafe(6),
    )
    db.add(campaign)
    await db.flush()

    db.add(CampaignMember(campaign_id=campaign.id, user_id=dm_user_id))
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def get_campaign_by_id(db: AsyncSession, campaign_id: int) -> Campaign | None:
    q = await db.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .options(selectinload(Campaign.members).selectinload(CampaignMember.user))
    )
    return q.scalar_one_or_none()


async def list_campaigns_for_user(db: AsyncSession, user_id: int) -> list[Campaign]:
    q = await db.execute(
        select(Campaign)
        .join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .where(CampaignMember.user_id == user_id)
        .options(selectinload(Campaign.members).selectinload(CampaignMember.user))
        .distinct()
    )
    return list(q.scalars().all())


async def join_campaign(db: AsyncSession, user_id: int, invite_code: str) -> Campaign | None:
    q = await db.execute(select(Campaign).where(Campaign.invite_code == invite_code))
    campaign = q.scalar_one_or_none()
    if not campaign:
        return None

    q = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.user_id == user_id,
        )
    )
    if not q.scalar_one_or_none():
        db.add(CampaignMember(campaign_id=campaign.id, user_id=user_id))
        await db.commit()

    # re-fetch with members eager-loaded (needed by the DM-facing response shape)
    return await get_campaign_by_id(db, campaign.id)


async def _detach_member_characters(db: AsyncSession, campaign_id: int, user_id: int) -> None:
    q = await db.execute(
        select(Character).where(
            Character.campaign_id == campaign_id,
            Character.owner_user_id == user_id,
        )
    )
    for ch in q.scalars().all():
        ch.campaign_id = None


async def leave_campaign(db: AsyncSession, user_id: int, campaign_id: int) -> bool:
    q = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
    )
    member = q.scalar_one_or_none()
    if not member:
        return False

    await _detach_member_characters(db, campaign_id, user_id)
    await db.delete(member)
    await db.commit()
    return True


async def kick_campaign_member(db: AsyncSession, campaign_id: int, dm_user_id: int, target_user_id: int) -> bool:
    campaign = await get_campaign_by_id(db, campaign_id)
    if not campaign or campaign.dm_user_id != dm_user_id or target_user_id == dm_user_id:
        return False

    q = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == target_user_id,
        )
    )
    member = q.scalar_one_or_none()
    if not member:
        return False

    await _detach_member_characters(db, campaign_id, target_user_id)
    await db.delete(member)
    await db.commit()
    return True


async def delete_campaign(db: AsyncSession, dm_user_id: int, campaign_id: int) -> bool:
    campaign = await get_campaign_by_id(db, campaign_id)
    if not campaign or campaign.dm_user_id != dm_user_id:
        return False

    q = await db.execute(select(Character).where(Character.campaign_id == campaign_id))
    for ch in q.scalars().all():
        ch.campaign_id = None

    await db.delete(campaign)
    await db.commit()
    return True


async def list_campaign_characters(db: AsyncSession, campaign_id: int, dm_user_id: int) -> list[Character] | None:
    campaign = await get_campaign_by_id(db, campaign_id)
    if not campaign or campaign.dm_user_id != dm_user_id:
        return None

    q = await db.execute(
        select(Character)
        .where(Character.campaign_id == campaign_id)
        .options(selectinload(Character.owner))
    )
    return list(q.scalars().all())


async def send_campaign_message(
    db: AsyncSession,
    campaign_id: int,
    sender_user_id: int,
    target_user_id: int | None,
    text: str,
) -> CampaignMessage | None:
    campaign = await get_campaign_by_id(db, campaign_id)
    if not campaign or campaign.dm_user_id != sender_user_id:
        return None

    if target_user_id is not None and not any(m.user_id == target_user_id for m in campaign.members):
        return None

    msg = CampaignMessage(
        campaign_id=campaign_id,
        sender_user_id=sender_user_id,
        target_user_id=target_user_id,
        text=text,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def list_campaign_messages(db: AsyncSession, campaign_id: int, viewer_user_id: int) -> list[CampaignMessage] | None:
    campaign = await get_campaign_by_id(db, campaign_id)
    if not campaign:
        return None

    is_dm = campaign.dm_user_id == viewer_user_id
    if not is_dm and not any(m.user_id == viewer_user_id for m in campaign.members):
        return None

    q = select(CampaignMessage).where(CampaignMessage.campaign_id == campaign_id)
    if not is_dm:
        q = q.where(
            (CampaignMessage.target_user_id.is_(None))
            | (CampaignMessage.target_user_id == viewer_user_id)
        )
    q = q.order_by(CampaignMessage.created_at.desc()).options(
        selectinload(CampaignMessage.sender), selectinload(CampaignMessage.target)
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def mark_campaign_messages_read(db: AsyncSession, campaign_id: int, user_id: int) -> bool:
    q = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
    )
    member = q.scalar_one_or_none()
    if not member:
        return False

    # anchor to the latest visible message's own created_at, not wall-clock time:
    # SQLite's CURRENT_TIMESTAMP (used for created_at) only has second precision,
    # so a message inserted in the same second as a client-clock "now" can compare
    # as older than last_read_at and get silently skipped by count_unread_campaign_messages
    q = await db.execute(
        select(func.max(CampaignMessage.created_at)).where(
            CampaignMessage.campaign_id == campaign_id,
            (CampaignMessage.target_user_id.is_(None)) | (CampaignMessage.target_user_id == user_id),
        )
    )
    latest = q.scalar_one_or_none()
    member.last_read_at = latest or datetime.utcnow()
    await db.commit()
    return True


async def count_unread_campaign_messages(db: AsyncSession, campaign_id: int, user_id: int) -> int:
    q = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
    )
    member = q.scalar_one_or_none()
    if not member:
        return 0

    since = member.last_read_at or datetime(1970, 1, 1)
    q = select(func.count()).select_from(CampaignMessage).where(
        CampaignMessage.campaign_id == campaign_id,
        CampaignMessage.created_at > since,
        (CampaignMessage.target_user_id.is_(None)) | (CampaignMessage.target_user_id == user_id),
    )
    result = await db.execute(q)
    return result.scalar_one()


# =========================
# ITEMS (INVENTORY)
# =========================

async def list_items(db: AsyncSession, character_id: int) -> list[Item]:
    q = await db.execute(select(Item).where(Item.character_id == character_id))
    return list(q.scalars().all())


async def add_item(
    db: AsyncSession,
    character_id: int,
    name: str,
    description: str,
    stats: str | None = None,
    qty: int = 1,
) -> Item:
    it = Item(
        character_id=character_id,
        name=name,
        description=description,
        stats=stats,
        qty=qty,
    )
    db.add(it)
    await db.commit()
    await db.refresh(it)
    return it


async def delete_item(db: AsyncSession, item_id: int) -> bool:
    q = await db.execute(select(Item).where(Item.id == item_id))
    item = q.scalar_one_or_none()
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True


async def update_item(db: AsyncSession, ch_id: int, item_id: int, data):
    item = await db.get(Item, item_id)
    if not item or item.character_id != ch_id:
        return None

    for field in ITEM_FIELDS:
        v = getattr(data, field, None)
        if v is not None:
            setattr(item, field, v)

    await db.commit()
    await db.refresh(item)
    return item


# =========================
# SPELLS
# =========================

async def add_spell(db: AsyncSession, character_id: int, payload: dict) -> Spell:
    sp = Spell(character_id=character_id, **payload)
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp


# =========================
# ABILITIES
# =========================

async def add_ability(db: AsyncSession, character_id: int, payload: dict) -> Ability:
    ab = Ability(character_id=character_id, **payload)
    db.add(ab)
    await db.commit()
    await db.refresh(ab)
    return ab


# =========================
# STATES
# =========================

async def add_state(db: AsyncSession, character_id: int, payload: dict) -> State:
    st = State(character_id=character_id, **payload)
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


async def update_spell(db: AsyncSession, ch_id: int, spell_id: int, data):
    obj = await db.get(Spell, spell_id)
    if not obj or obj.character_id != ch_id:
        return None

    for f in SPELL_FIELDS:
        v = getattr(data, f, None)
        if v is not None:
            setattr(obj, f, v)

    await db.commit()
    await db.refresh(obj)
    return obj


async def update_ability(db: AsyncSession, ch_id: int, ability_id: int, data):
    obj = await db.get(Ability, ability_id)
    if not obj or obj.character_id != ch_id:
        return None

    for f in ABILITY_FIELDS:
        v = getattr(data, f, None)
        if v is not None:
            setattr(obj, f, v)

    await db.commit()
    await db.refresh(obj)
    return obj


async def update_state(db: AsyncSession, ch_id: int, state_id: int, data):
    obj = await db.get(State, state_id)
    if not obj or obj.character_id != ch_id:
        return None

    for f in STATE_FIELDS:
        v = getattr(data, f, None)
        if v is not None:
            setattr(obj, f, v)

    await db.commit()
    await db.refresh(obj)
    return obj


# =========================
# SUMMONS
# =========================

async def list_summons(db: AsyncSession, character_id: int) -> list[Summon]:
    q = await db.execute(select(Summon).where(Summon.character_id == character_id))
    return list(q.scalars().all())


async def add_summon(db: AsyncSession, character_id: int, payload: dict) -> Summon:
    obj = Summon(character_id=character_id, **payload)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_summon(db: AsyncSession, ch_id: int, summon_id: int, data) -> Summon | None:
    obj = await db.get(Summon, summon_id)
    if not obj or obj.character_id != ch_id:
        return None

    for field in SUMMON_FIELDS:
        v = getattr(data, field, None)
        if v is not None:
            setattr(obj, field, v)

    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_summon(db: AsyncSession, summon_id: int) -> bool:
    obj = await db.get(Summon, summon_id)
    if not obj:
        return False
    await db.delete(obj)
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
    q = await db.execute(
        select(SheetTemplate).where(
            SheetTemplate.id == template_id,
            SheetTemplate.owner_user_id == user_id,
        )
    )
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


async def apply_template_to_character(
    db: AsyncSession,
    character_id: int,
    user_id: int,
    template_id: int,
) -> Character | None:
    ch = await get_character_for_user(db, character_id, user_id)
    if not ch:
        return None

    q = await db.execute(
        select(SheetTemplate).where(
            SheetTemplate.id == template_id,
            SheetTemplate.owner_user_id == user_id,
        )
    )
    tpl = q.scalar_one_or_none()
    if not tpl:
        return None

    config = _safe_json_dict(tpl.config_json)
    cur = _safe_json_dict(ch.custom_values)

    for k, v in _tpl_defaults(config).items():
        cur.setdefault(k, v)

    ch.template_id = tpl.id
    ch.custom_values = json.dumps(cur, ensure_ascii=False)

    await db.commit()
    await db.refresh(ch)
    return ch


async def create_character_from_template(
    db: AsyncSession,
    user_id: int,
    template_id: int,
    name: str,
) -> Character | None:
    q = await db.execute(
        select(SheetTemplate).where(
            SheetTemplate.id == template_id,
            SheetTemplate.owner_user_id == user_id,
        )
    )
    if not q.scalar_one_or_none():
        return None

    ch = await create_character(db, user_id, name)
    return await apply_template_to_character(db, ch.id, user_id, template_id)


async def update_custom_values(db: AsyncSession, character_id: int, user_id: int, values: dict) -> bool:
    ch = await get_character_for_user(db, character_id, user_id)
    if not ch:
        return False

    cur = _safe_json_dict(ch.custom_values)

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
    summons = await list_summons(db, character_id)
    eq = await get_or_create_equipment(db, character_id)

    tpl = None
    config = None
    if ch.template_id:
        q = await db.execute(select(SheetTemplate).where(SheetTemplate.id == ch.template_id))
        tpl = q.scalar_one_or_none()
        if tpl:
            config = _safe_json_dict(tpl.config_json)

    custom = _safe_json_dict(ch.custom_values)

    return {
        "character": ch,
        "items": items,
        "spells": spells,
        "abilities": abilities,
        "states": states,
        "summons": summons,
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

            "aggression": ch.aggression,
            "kindness": ch.kindness,
            "intellect": ch.intellect,
            "fearlessness": ch.fearlessness,
            "confidence": ch.confidence,
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
            {
                "name": i.name,
                "description": i.description,
                "stats": i.stats,
                "qty": i.qty,
            }
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
        "summons": [
            {
                "name": s.name,
                "description": s.description,
                "duration": s.duration,
                "hp_ratio": s.hp_ratio,
                "attack_ratio": s.attack_ratio,
                "defense_ratio": s.defense_ratio,

                "mana_ratio": s.mana_ratio,
                "energy_ratio": s.energy_ratio,
                "initiative_ratio": s.initiative_ratio,
                "luck_ratio": s.luck_ratio,
                "steps_ratio": s.steps_ratio,
                "attack_range_ratio": s.attack_range_ratio,

                "count": s.count,
            }
            for s in sheet.get("summons", [])
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
    name = str(payload.get("new_name") or ch_data.get("name") or "Character")
    ch = await create_character(db, user_id, name)

    # set fields on character
    for key, value in ch_data.items():
        if hasattr(ch, key) and value is not None:
            setattr(ch, key, value)

    # new_name wins over character.name from the imported JSON, even
    # though the loop above just copied character.name onto ch.name
    if payload.get("new_name"):
        ch.name = str(payload.get("new_name"))

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
            await add_item(
                db,
                ch.id,
                i.get("name"),
                i.get("description", ""),
                i.get("stats", ""),
                qty=int(i.get("qty", 1) or 1),
            )

    # spells
    for s in payload.get("spells") or []:
        if isinstance(s, dict) and s.get("name"):
            await add_spell(
                db,
                ch.id,
                {
                    "name": s.get("name"),
                    "description": s.get("description", ""),
                    "range": s.get("range", ""),
                    "duration": s.get("duration", ""),
                    "cost": s.get("cost", ""),
                },
            )

    # abilities
    for a in payload.get("abilities") or []:
        if isinstance(a, dict) and a.get("name"):
            await add_ability(
                db,
                ch.id,
                {
                    "name": a.get("name"),
                    "description": a.get("description", ""),
                    "range": a.get("range", ""),
                    "duration": a.get("duration", ""),
                    "cost": a.get("cost", ""),
                },
            )

    # states
    for st in payload.get("states") or []:
        if isinstance(st, dict) and st.get("name"):
            await add_state(
                db,
                ch.id,
                {
                    "name": st.get("name"),
                    "hp_cost": int(st.get("hp_cost", 0) or 0),
                    "duration": st.get("duration", ""),
                    "is_active": bool(st.get("is_active", True)),
                },
            )

    # summons
    for sm in payload.get("summons") or []:
        if isinstance(sm, dict) and sm.get("name"):
            await add_summon(
                db,
                ch.id,
                {
                    "name": sm.get("name"),
                    "description": sm.get("description", ""),
                    "duration": sm.get("duration", ""),
                    "hp_ratio": sm.get("hp_ratio", "1/3"),
                    "attack_ratio": sm.get("attack_ratio", "1/2"),
                    "defense_ratio": sm.get("defense_ratio", "1/4"),

                    "mana_ratio": sm.get("mana_ratio", "0"),
                    "energy_ratio": sm.get("energy_ratio", "0"),
                    "initiative_ratio": sm.get("initiative_ratio", "0"),
                    "luck_ratio": sm.get("luck_ratio", "0"),
                    "steps_ratio": sm.get("steps_ratio", "0"),
                    "attack_range_ratio": sm.get("attack_range_ratio", "0"),

                    "count": int(sm.get("count", 1) or 1),
                },
            )
    return ch


# Backward-compatible aliases
async def export_sheet(db: AsyncSession, character_id: int, user_id: int) -> dict | None:
    return await export_character(db, character_id, user_id)


async def import_sheet(db: AsyncSession, user_id: int, payload: dict) -> Character:
    return await import_character(db, user_id, payload)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .deps import get_current_user
from .models import User
from . import crud, schemas

router = APIRouter()


def _member_label(user: User) -> str:
    return user.first_name or (f"@{user.username}" if user.username else f"Игрок #{user.id}")


async def _campaign_out(db: AsyncSession, campaign, viewer_id: int) -> dict:
    is_dm = campaign.dm_user_id == viewer_id
    out = {
        "id": campaign.id,
        "name": campaign.name,
        "is_dm": is_dm,
        "unread_count": 0,
    }
    if is_dm:
        out["invite_code"] = campaign.invite_code
        out["members"] = [
            {"user_id": m.user_id, "name": _member_label(m.user)}
            for m in campaign.members
            if m.user_id != campaign.dm_user_id
        ]
    else:
        out["unread_count"] = await crud.count_unread_campaign_messages(db, campaign.id, viewer_id)
    return out


@router.post("")
async def create_campaign(
    body: schemas.CampaignCreate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")
    campaign = await crud.create_campaign(db, u.id, name)
    return {"id": campaign.id, "name": campaign.name, "invite_code": campaign.invite_code}


@router.get("")
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    campaigns = await crud.list_campaigns_for_user(db, u.id)
    return [await _campaign_out(db, c, u.id) for c in campaigns]


@router.post("/join")
async def join_campaign(
    body: schemas.CampaignJoin,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    campaign = await crud.join_campaign(db, u.id, body.invite_code.strip())
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    return await _campaign_out(db, campaign, u.id)


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    ok = await crud.delete_campaign(db, u.id, campaign_id)
    if not ok:
        raise HTTPException(404, "Campaign not found")
    return {"status": "ok"}


@router.delete("/{campaign_id}/leave")
async def leave_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    ok = await crud.leave_campaign(db, u.id, campaign_id)
    if not ok:
        raise HTTPException(404, "Not a member of this campaign")
    return {"status": "ok"}


@router.delete("/{campaign_id}/members/{user_id}")
async def kick_campaign_member(
    campaign_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    ok = await crud.kick_campaign_member(db, campaign_id, u.id, user_id)
    if not ok:
        raise HTTPException(404, "Not found")
    return {"status": "ok"}


@router.get("/{campaign_id}/characters")
async def list_campaign_characters(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    chars = await crud.list_campaign_characters(db, campaign_id, u.id)
    if chars is None:
        raise HTTPException(403, "DM access required")
    return [
        {
            "id": c.id,
            "name": c.name,
            "level": c.level,
            "owner_name": _member_label(c.owner),
        }
        for c in chars
    ]


@router.post("/{campaign_id}/messages")
async def send_message(
    campaign_id: int,
    body: schemas.MessageCreate,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Text is required")

    msg = await crud.send_campaign_message(db, campaign_id, u.id, body.target_user_id, text)
    if not msg:
        raise HTTPException(403, "DM access required, or target is not a campaign member")
    return {"status": "ok", "id": msg.id}


@router.get("/{campaign_id}/messages")
async def list_messages(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    rows = await crud.list_campaign_messages(db, campaign_id, u.id)
    if rows is None:
        raise HTTPException(403, "No access")
    return [
        {
            "id": m.id,
            "sender_name": _member_label(m.sender),
            "target_user_id": m.target_user_id,
            "target_name": _member_label(m.target) if m.target else None,
            "text": m.text,
            "created_at": m.created_at.isoformat(),
            "is_unread": is_unread,
        }
        for m, is_unread in rows
    ]


@router.delete("/{campaign_id}/messages/{message_id}")
async def hide_message(
    campaign_id: int,
    message_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    ok = await crud.hide_campaign_message(db, campaign_id, u.id, message_id)
    if not ok:
        raise HTTPException(404, "Not a member of this campaign")
    return {"status": "ok"}


@router.post("/{campaign_id}/messages/read")
async def mark_messages_read(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    ok = await crud.mark_campaign_messages_read(db, campaign_id, u.id)
    if not ok:
        raise HTTPException(404, "Not a member of this campaign")
    return {"status": "ok"}


def _battle_out(battle, viewer_id: int, is_dm: bool) -> dict:
    participants = []
    for p in battle.participants:
        ch = p.character
        can_see_resources = battle.reveal_resources or is_dm or ch.owner_user_id == viewer_id
        item = {
            "character_id": ch.id,
            "name": ch.name,
            "initiative": ch.initiative,
            "is_current_turn": p.order_index == battle.turn_index,
        }
        if can_see_resources:
            item.update({
                "hp": ch.hp, "hp_max": ch.hp_max,
                "mana": ch.mana, "mana_max": ch.mana_max,
                "energy": ch.energy, "energy_max": ch.energy_max,
            })
        participants.append(item)

    current = battle.participants[battle.turn_index]
    return {
        "round": battle.round,
        "reveal_resources": battle.reveal_resources,
        "current_turn_character_id": current.character_id,
        "participants": participants,
    }


@router.post("/{campaign_id}/battle")
async def start_battle(
    campaign_id: int,
    body: schemas.BattleStart,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    battle = await crud.start_campaign_battle(db, campaign_id, u.id, body.character_ids, body.reveal_resources)
    if not battle:
        raise HTTPException(400, "Cannot start battle (not DM, battle already active, or invalid characters)")
    return _battle_out(battle, u.id, is_dm=True)


@router.get("/{campaign_id}/battle")
async def get_battle(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    campaign = await crud.get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    battle = await crud.get_campaign_battle(db, campaign_id, u.id)
    if battle is None:
        is_member = campaign.dm_user_id == u.id or any(m.user_id == u.id for m in campaign.members)
        if not is_member:
            raise HTTPException(403, "No access")
        return None
    return _battle_out(battle, u.id, is_dm=campaign.dm_user_id == u.id)


@router.post("/{campaign_id}/battle/next-turn")
async def next_turn(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    campaign = await crud.get_campaign_by_id(db, campaign_id)
    battle = await crud.advance_battle_turn(db, campaign_id, u.id)
    if not battle:
        raise HTTPException(403, "No active battle, or not your turn")
    return _battle_out(battle, u.id, is_dm=bool(campaign and campaign.dm_user_id == u.id))


@router.delete("/{campaign_id}/battle")
async def end_battle(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    u: User = Depends(get_current_user),
):
    ok = await crud.end_campaign_battle(db, campaign_id, u.id)
    if not ok:
        raise HTTPException(403, "DM access required, or no active battle")
    return {"status": "ok"}

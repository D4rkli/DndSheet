from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean, UniqueConstraint

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)
    vk_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)

    # кэш имени из последнего логина — нужен, чтобы ДМ мог видеть, чей персонаж
    # (сам User больше ничего о профиле не хранит, это не источник истины)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    username: Mapped[str | None] = mapped_column(String(120), nullable=True)

    characters: Mapped[list["Character"]] = relationship(back_populates="owner")

    templates: Mapped[list["SheetTemplate"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    dm_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    dm: Mapped["User"] = relationship(foreign_keys=[dm_user_id])
    members: Mapped[list["CampaignMember"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    characters: Mapped[list["Character"]] = relationship(back_populates="campaign")


class CampaignMember(Base):
    __tablename__ = "campaign_members"
    __table_args__ = (UniqueConstraint("campaign_id", "user_id", name="uq_campaign_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # JSON array of campaign_messages.id this member has personally hidden
    # from their own inbox (doesn't affect other members' view of the message)
    hidden_message_ids: Mapped[str] = mapped_column(Text, default="")

    campaign: Mapped["Campaign"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class CampaignMessage(Base):
    __tablename__ = "campaign_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    # Python-side default (not server_default=func.now()): SQLite's CURRENT_TIMESTAMP
    # only has second precision, which could make a message inserted in the same
    # second as a read-mark compare as "not newer" and be skipped by unread counts.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["Campaign"] = relationship()
    sender: Mapped["User"] = relationship(foreign_keys=[sender_user_id])
    target: Mapped["User | None"] = relationship(foreign_keys=[target_user_id])


class CampaignBattle(Base):
    __tablename__ = "campaign_battles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), unique=True, index=True)
    round: Mapped[int] = mapped_column(Integer, default=1)
    turn_index: Mapped[int] = mapped_column(Integer, default=0)
    reveal_resources: Mapped[bool] = mapped_column(Boolean, default=True)

    campaign: Mapped["Campaign"] = relationship()
    participants: Mapped[list["CampaignBattleParticipant"]] = relationship(
        back_populates="battle",
        cascade="all, delete-orphan",
        order_by="CampaignBattleParticipant.order_index",
    )


class CampaignBattleParticipant(Base):
    __tablename__ = "campaign_battle_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    battle_id: Mapped[int] = mapped_column(ForeignKey("campaign_battles.id"), index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    battle: Mapped["CampaignBattle"] = relationship(back_populates="participants")
    character: Mapped["Character"] = relationship()


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(100))
    race: Mapped[str] = mapped_column(String(60), default="")
    gender: Mapped[str] = mapped_column(String(40), default="")
    klass: Mapped[str] = mapped_column(String(60), default="")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    xp_per_level: Mapped[int] = mapped_column(Integer, default=0)

    # Деньги
    gold: Mapped[int] = mapped_column(Integer, default=0)
    silver: Mapped[int] = mapped_column(Integer, default=0)
    copper: Mapped[int] = mapped_column(Integer, default=0)

    # “Характер” (можно расширять)
    aggression: Mapped[int] = mapped_column(Integer, default=0)
    kindness: Mapped[int] = mapped_column(Integer, default=0)
    intellect: Mapped[int] = mapped_column(Integer, default=0)
    fearlessness: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    humor: Mapped[int] = mapped_column(Integer, default=0)
    emotionality: Mapped[int] = mapped_column(Integer, default=0)
    sociability: Mapped[int] = mapped_column(Integer, default=0)
    responsibility: Mapped[int] = mapped_column(Integer, default=0)
    intimidation: Mapped[int] = mapped_column(Integer, default=0)
    attentiveness: Mapped[int] = mapped_column(Integer, default=0)
    learnability: Mapped[int] = mapped_column(Integer, default=0)
    luck: Mapped[int] = mapped_column(Integer, default=0)
    stealth: Mapped[int] = mapped_column(Integer, default=0)

    # Боевые параметры
    initiative: Mapped[int] = mapped_column(Integer, default=0)
    attack: Mapped[int] = mapped_column(Integer, default=0)
    counterattack: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[int] = mapped_column(Integer, default=0)
    defense: Mapped[int] = mapped_column(Integer, default=0)
    perm_armor: Mapped[int] = mapped_column(Integer, default=0)
    temp_armor: Mapped[int] = mapped_column(Integer, default=0)
    action_points: Mapped[int] = mapped_column(Integer, default=0)
    dodges: Mapped[int] = mapped_column(Integer, default=0)

    # РЕСУРСЫ (текущее)
    hp: Mapped[int] = mapped_column(Integer, default=0)
    mana: Mapped[int] = mapped_column(Integer, default=0)
    energy: Mapped[int] = mapped_column(Integer, default=0)

    # РЕСУРСЫ (макс)
    hp_max: Mapped[int] = mapped_column(Integer, default=0)
    mana_max: Mapped[int] = mapped_column(Integer, default=0)
    energy_max: Mapped[int] = mapped_column(Integer, default=0)

    # Прибавка за уровень
    hp_per_level: Mapped[int] = mapped_column(Integer, default=0)
    mana_per_level: Mapped[int] = mapped_column(Integer, default=0)
    energy_per_level: Mapped[int] = mapped_column(Integer, default=0)

    level_up_rules: Mapped[str] = mapped_column(Text, default="")

    owner: Mapped["User"] = relationship(back_populates="characters")
    campaign: Mapped["Campaign | None"] = relationship(back_populates="characters", foreign_keys=[campaign_id])
    items: Mapped[list["Item"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    spells: Mapped[list["Spell"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    abilities: Mapped[list["Ability"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    states: Mapped[list["State"]] = relationship(back_populates="character", cascade="all, delete-orphan")

    summons: Mapped[list["Summon"]] = relationship(back_populates="character", cascade="all, delete-orphan")

    action_log: Mapped[list["ActionLogEntry"]] = relationship(back_populates="character", cascade="all, delete-orphan")

    equipment: Mapped["Equipment"] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        uselist=False,
    )

    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("sheet_templates.id"),
        nullable=True
    )

    custom_values: Mapped[str] = mapped_column(Text, default="{}")

    template: Mapped["SheetTemplate | None"] = relationship(
        foreign_keys=[template_id]
    )

class SheetTemplate(Base):
    __tablename__ = "sheet_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True
    )

    name: Mapped[str] = mapped_column(String(120))
    config_json: Mapped[str] = mapped_column(Text, default="{}")

    owner: Mapped["User"] = relationship(
        back_populates="templates",
        foreign_keys=[owner_user_id],
    )



class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    stats: Mapped[str] = mapped_column(Text, default="")  # можно JSON-строкой
    qty: Mapped[int] = mapped_column(Integer, default=1)

    character: Mapped["Character"] = relationship(back_populates="items")

class Spell(Base):
    __tablename__ = "spells"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)

    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    range: Mapped[str] = mapped_column(String(80), default="")
    duration: Mapped[str] = mapped_column(String(80), default="")
    cost: Mapped[str] = mapped_column(String(120), default="")  # “мана = x*10” и т.д.
    level: Mapped[int] = mapped_column(Integer, default=0)
    ap_cost: Mapped[int] = mapped_column(Integer, default=5)

    character: Mapped["Character"] = relationship(back_populates="spells")

class Ability(Base):
    __tablename__ = "abilities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)

    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    range: Mapped[str] = mapped_column(String(80), default="")
    duration: Mapped[str] = mapped_column(String(80), default="")
    cost: Mapped[str] = mapped_column(String(120), default="")
    level: Mapped[int] = mapped_column(Integer, default=0)
    ap_cost: Mapped[int] = mapped_column(Integer, default=1)

    character: Mapped["Character"] = relationship(back_populates="abilities")

class State(Base):
    __tablename__ = "states"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)

    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String, default="")
    hp_cost: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[str] = mapped_column(String(80), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    character: Mapped["Character"] = relationship(back_populates="states")

class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), unique=True)

    head: Mapped[str] = mapped_column(String(120), default="")
    armor: Mapped[str] = mapped_column(String(120), default="")
    back: Mapped[str] = mapped_column(String(120), default="")
    hands: Mapped[str] = mapped_column(String(120), default="")
    legs: Mapped[str] = mapped_column(String(120), default="")
    feet: Mapped[str] = mapped_column(String(120), default="")
    weapon1: Mapped[str] = mapped_column(String(120), default="")
    weapon2: Mapped[str] = mapped_column(String(120), default="")
    belt: Mapped[str] = mapped_column(String(120), default="")
    ring1: Mapped[str] = mapped_column(String(120), default="")
    ring2: Mapped[str] = mapped_column(String(120), default="")
    ring3: Mapped[str] = mapped_column(String(120), default="")
    ring4: Mapped[str] = mapped_column(String(120), default="")
    jewelry: Mapped[str] = mapped_column(String(120), default="")

    character: Mapped["Character"] = relationship(back_populates="equipment")

class Summon(Base):
    __tablename__ = "summons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)

    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[str] = mapped_column(String(80), default="")

    # коэффициенты/доли (строками: "1/3", "50%", "0.25")
    hp_ratio: Mapped[str] = mapped_column(String(40), default="1/3")
    attack_ratio: Mapped[str] = mapped_column(String(40), default="1/2")
    defense_ratio: Mapped[str] = mapped_column(String(40), default="1/4")
    # дополнительные параметры (строками, как доли/проценты/формулы)
    mana_ratio: Mapped[str] = mapped_column(String(40), default="0")
    energy_ratio: Mapped[str] = mapped_column(String(40), default="0")
    initiative_ratio: Mapped[str] = mapped_column(String(40), default="0")
    luck_ratio: Mapped[str] = mapped_column(String(40), default="0")
    steps_ratio: Mapped[str] = mapped_column(String(40), default="0")
    attack_range_ratio: Mapped[str] = mapped_column(String(40), default="0")

    count: Mapped[int] = mapped_column(Integer, default=1)

    character: Mapped["Character"] = relationship(back_populates="summons")


class ActionLogEntry(Base):
    __tablename__ = "action_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    character: Mapped["Character"] = relationship(back_populates="action_log")


class FeedbackReport(Base):
    __tablename__ = "feedback_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))  # "bug" | "suggestion"
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship()

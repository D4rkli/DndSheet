from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, ForeignKey, Boolean

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    characters: Mapped[list["Character"]] = relationship(back_populates="owner")

class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(100))
    race: Mapped[str] = mapped_column(String(60), default="")
    gender: Mapped[str] = mapped_column(String(40), default="")
    klass: Mapped[str] = mapped_column(String(60), default="")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)

    # “Характер” (можно расширять)
    aggression_kindness: Mapped[int] = mapped_column(Integer, default=0)
    intellect: Mapped[int] = mapped_column(Integer, default=0)
    fearlessness: Mapped[int] = mapped_column(Integer, default=0)
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
    items: Mapped[list["Item"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    spells: Mapped[list["Spell"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    abilities: Mapped[list["Ability"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    states: Mapped[list["State"]] = relationship(back_populates="states", cascade="all, delete-orphan")

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    stats: Mapped[str] = mapped_column(Text, default="")  # можно JSON-строкой

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

    character: Mapped["Character"] = relationship(back_populates="abilities")

class State(Base):
    __tablename__ = "states"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)

    name: Mapped[str] = mapped_column(String(80))
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

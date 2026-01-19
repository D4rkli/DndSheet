from pydantic import BaseModel
from typing import Optional


class CharacterCreate(BaseModel):
    name: str


class CharacterUpdate(BaseModel):
    # базовое
    name: Optional[str] = None
    race: Optional[str] = None
    klass: Optional[str] = None
    level: Optional[int] = None

    # текущие ресурсы
    hp: Optional[int] = None
    mana: Optional[int] = None
    energy: Optional[int] = None

    # максимумы
    hp_max: Optional[int] = None
    mana_max: Optional[int] = None
    energy_max: Optional[int] = None

    # прибавка за уровень
    hp_per_level: Optional[int] = None
    mana_per_level: Optional[int] = None
    energy_per_level: Optional[int] = None

    # остальное (твои характеристики / боевые статы)
    aggression_kindness: Optional[int] = None
    intellect: Optional[int] = None
    fearlessness: Optional[int] = None
    humor: Optional[int] = None
    emotionality: Optional[int] = None
    sociability: Optional[int] = None
    responsibility: Optional[int] = None
    intimidation: Optional[int] = None
    attentiveness: Optional[int] = None
    learnability: Optional[int] = None
    luck: Optional[int] = None
    stealth: Optional[int] = None

    initiative: Optional[int] = None
    attack: Optional[int] = None
    counterattack: Optional[int] = None
    steps: Optional[int] = None
    defense: Optional[int] = None
    perm_armor: Optional[int] = None
    temp_armor: Optional[int] = None
    action_points: Optional[int] = None
    dodges: Optional[int] = None

    level_up_rules: Optional[str] = None


class ItemCreate(BaseModel):
    name: str
    description: str = ""
    stats: str = ""


class SpellCreate(BaseModel):
    name: str
    description: str = ""
    range: str = ""
    duration: str = ""
    cost: str = ""


class AbilityCreate(SpellCreate):
    pass


class StateCreate(BaseModel):
    name: str
    hp_cost: int = 0
    duration: str = ""
    is_active: bool = True

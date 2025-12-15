from pydantic import BaseModel
from typing import Optional

class CharacterCreate(BaseModel):
    name: str

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    race: Optional[str] = None
    klass: Optional[str] = None
    level: Optional[int] = None

    hp: Optional[int] = None
    mana: Optional[int] = None
    energy: Optional[int] = None


    aggression_kindness: int | None = None
    intellect: int | None = None
    fearlessness: int | None = None
    humor: int | None = None
    emotionality: int | None = None
    sociability: int | None = None
    responsibility: int | None = None
    intimidation: int | None = None
    attentiveness: int | None = None
    learnability: int | None = None
    luck: int | None = None
    stealth: int | None = None

    hp: int | None = None
    mana: int | None = None
    initiative: int | None = None
    attack: int | None = None
    energy: int | None = None
    counterattack: int | None = None
    steps: int | None = None
    defense: int | None = None
    perm_armor: int | None = None
    temp_armor: int | None = None
    action_points: int | None = None
    dodges: int | None = None

    level_up_rules: str | None = None

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

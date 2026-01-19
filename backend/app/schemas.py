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

    hp_max: Optional[int] = None
    mana_max: Optional[int] = None
    energy_max: Optional[int] = None

    # прибавка за уровень
    hp_per_level: Optional[int] = None
    mana_per_level: Optional[int] = None
    energy_per_level: Optional[int] = None

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

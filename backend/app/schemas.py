# app/schemas.py
from pydantic import BaseModel
from typing import Optional, Any, Dict

class CharacterCreate(BaseModel):
    name: str

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    race: Optional[str] = None
    klass: Optional[str] = None
    level: Optional[int] = None

    # текущее
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
    qty: int = 1

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    stats: Optional[str] = None
    qty: Optional[int] = None


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

class SpellUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    range: Optional[str] = None
    duration: Optional[str] = None
    cost: Optional[str] = None

class AbilityUpdate(SpellUpdate):
    pass

class StateUpdate(BaseModel):
    name: Optional[str] = None
    hp_cost: Optional[int] = None
    duration: Optional[str] = None
    is_active: Optional[bool] = None

class EquipmentUpdate(BaseModel):
    head: Optional[str] = None
    armor: Optional[str] = None
    back: Optional[str] = None
    hands: Optional[str] = None
    legs: Optional[str] = None
    feet: Optional[str] = None
    weapon1: Optional[str] = None
    weapon2: Optional[str] = None
    belt: Optional[str] = None
    ring1: Optional[str] = None
    ring2: Optional[str] = None
    ring3: Optional[str] = None
    ring4: Optional[str] = None
    jewelry: Optional[str] = None


class SheetTemplateCreate(BaseModel):
    name: str
    # произвольная конфигурация (вкладки, поля, версия и т.п.)
    config: Dict[str, Any] = {}


class SheetTemplateOut(BaseModel):
    id: int
    name: str
    config: Dict[str, Any] = {}


class SheetExportOut(BaseModel):
    """Полный экспорт листа в JSON."""
    character: Dict[str, Any]
    items: list[Dict[str, Any]]
    spells: list[Dict[str, Any]]
    abilities: list[Dict[str, Any]]
    states: list[Dict[str, Any]]
    equipment: Optional[Dict[str, Any]] = None


class SheetImportIn(SheetExportOut):
    # при импорте можно переименовать
    new_name: Optional[str] = None



class ApplyTemplate(BaseModel):
    template_id: int


class CustomValuesUpdate(BaseModel):
    values: Dict[str, Any]


class ImportPayload(BaseModel):
    # optional template to create on import
    template: Optional[Dict[str, Any]] = None
    character: Dict[str, Any]
    items: list[Dict[str, Any]] = []
    spells: list[Dict[str, Any]] = []
    abilities: list[Dict[str, Any]] = []
    states: list[Dict[str, Any]] = []
    equipment: Optional[Dict[str, Any]] = None
    custom_values: Optional[Dict[str, Any]] = None

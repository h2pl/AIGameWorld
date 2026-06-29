"""物品领域模型 / Item Domain Model."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ItemType(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    POTION = "potion"
    SCROLL = "scroll"
    KEY = "key"
    CONSUMABLE = "consumable"
    MISC = "misc"


class Item(BaseModel):
    """全局物品定义."""

    id: str
    name: str
    item_type: ItemType
    rarity: str = "common"
    weight: float = 0.0
    value: int = 0
    description: str = ""
    data: dict = Field(default_factory=dict)
    pack_name: str = ""

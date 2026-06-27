"""Item and ItemType Pydantic models.

Based on docs/06-data-layer.md §5.2b.
Architecture spec §6.8 (Item system).
"""

from enum import Enum

from pydantic import BaseModel, Field


class ItemType(str, Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    POTION = "potion"
    SCROLL = "scroll"
    KEY = "key"
    CONSUMABLE = "consumable"
    MISC = "misc"


class Item(BaseModel):
    """Global item definition – referenced by PC / Actor / SceneObject."""

    id: str
    name: str
    item_type: ItemType
    rarity: str = "common"  # common / uncommon / rare / legendary / artifact
    weight: float = 0.0
    value: int = 0  # base price in gold
    description: str = ""
    data: dict = Field(default_factory=dict)  # type-specific data (damage_dice, ac, ...)
    pack_name: str = ""

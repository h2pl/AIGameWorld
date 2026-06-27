"""SceneObject Pydantic model.

Based on docs/06-data-layer.md §5.2c.
Architecture spec §6.10 (SceneObject).
"""

from enum import Enum

from pydantic import BaseModel, Field


class SceneObjectType(str, Enum):
    CONTAINER = "container"  # chest / cabinet / bag
    DOOR = "door"  # door / gate / portal
    TRAP = "trap"  # trap
    ANIMAL = "animal"  # animal (no decision capability)
    MECHANISM = "mechanism"  # mechanism / altar / console
    DECORATION = "decoration"  # pure decoration
    ITEM_DROP = "item_drop"  # dropped items on ground


class SceneObject(BaseModel):
    """Non-autonomous scene entity – references Item ids in interact_data."""

    id: str
    name: str
    object_type: SceneObjectType
    scene_id: str = ""
    position_x: int = 0
    position_y: int = 0
    interactable: bool = True
    interact_data: dict | None = None  # references Item ids or stores interaction data

"""场景物体领域模型 / SceneObject Domain Model."""
from enum import Enum
from pydantic import BaseModel, Field


class SceneObjectType(str, Enum):
    CONTAINER = "container"
    DOOR = "door"
    TRAP = "trap"
    ANIMAL = "animal"
    MECHANISM = "mechanism"
    DECORATION = "decoration"
    ITEM_DROP = "item_drop"


class SceneObject(BaseModel):
    """场景中不能自主行动的实体."""

    id: str
    name: str
    object_type: SceneObjectType
    scene_id: str = ""
    position_x: int = 0
    position_y: int = 0
    interactable: bool = True
    interact_data: dict | None = None

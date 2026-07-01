"""场景物体领域模型 / SceneObject Domain Model."""

from enum import StrEnum

from .base import DomainModel


class SceneObjectType(StrEnum):
    CONTAINER = "container"
    DOOR = "door"
    TRAP = "trap"
    ANIMAL = "animal"
    MECHANISM = "mechanism"
    DECORATION = "decoration"
    ITEM_DROP = "item_drop"


class SceneObject(DomainModel):
    """场景中不能自主行动的实体."""

    id: str
    name: str
    object_type: SceneObjectType
    scene_id: str = ""
    position_x: int = 0
    position_y: int = 0
    interactable: bool = True
    interact_data: dict | None = None

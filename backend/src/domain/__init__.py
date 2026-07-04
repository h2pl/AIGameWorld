"""AIGameWorld 领域模型层 / Domain layer.

所有模型与 DB 表一一对应，继承 DomainModel（含 world_id + ext_json）。
All models map 1:1 to DB tables, inherit DomainModel (with world_id + ext_json).
"""

from .actor import Actor
from .base import DomainModel
from .dm_record import DMRecord
from .event import SEQUENCE, TICK_EVENT_SEQUENCE, Event, TickEvent, TickEventType
from .item import Item, ItemType
from .player_character import PlayerCharacter
from .scene import Scene
from .scene_object import SceneObject, SceneObjectType
from .story_summary import StorySummary
from .world import World

__all__ = [
    "Actor",
    "DMRecord",
    "DomainModel",
    "Event",
    "TickEvent",
    "TickEventType",
    "Item",
    "ItemType",
    "PlayerCharacter",
    "Scene",
    "SceneObject",
    "SceneObjectType",
    "SEQUENCE",
    "TICK_EVENT_SEQUENCE",
    "StorySummary",
    "World",
]

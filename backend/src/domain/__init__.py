"""AIGameWorld 领域模型层 / Domain layer.

所有模型与 DB 表一一对应，继承 DomainModel（含 world_id + ext_json）。
All models map 1:1 to DB tables, inherit DomainModel (with world_id + ext_json).
"""

from .action import Action
from .actor import Actor
from .base import DomainModel
from .combat_result import CombatActionResult
from .decision import Decision
from .dm_record import DMRecord
from .event import SEQUENCE, TICK_EVENT_SEQUENCE, Event, TickEvent, TickEventType
from .explore_result import ExploreActionResult
from .interact_result import InteractActionResult
from .item import Item, ItemType
from .memory import EntityType, Memory, MemoryPeriod, MemoryType, importance_of
from .player_character import PlayerCharacter
from .scene import Scene
from .scene_object import SceneObject, SceneObjectType
from .story_summary import StorySummary
from .talk_result import TalkActionResult
from .world import World

# 统一导出所有领域模型，供 service / engine / graph 共享类型
# Re-export all domain models for shared use across service, engine and graph layers.
__all__ = [
    "Action",
    "Actor",
    "CombatActionResult",
    "Decision",
    "DMRecord",
    "DomainModel",
    "EntityType",
    "Event",
    "ExploreActionResult",
    "InteractActionResult",
    "Item",
    "ItemType",
    "Memory",
    "MemoryPeriod",
    "MemoryType",
    "PlayerCharacter",
    "Scene",
    "SceneObject",
    "SceneObjectType",
    "SEQUENCE",
    "StorySummary",
    "TalkActionResult",
    "TickEvent",
    "TickEventType",
    "TICK_EVENT_SEQUENCE",
    "World",
    "importance_of",
]

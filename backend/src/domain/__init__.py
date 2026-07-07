"""AIGameWorld 领域模型层 / Domain layer.

所有模型与 DB 表一一对应，继承 DomainModel（含 world_id + ext_json）。
All models map 1:1 to DB tables, inherit DomainModel (with world_id + ext_json).
"""

from .action import Action
from .actor import Actor
from .base import DomainModel
from .decision import Decision
from .dm_record import DMRecord
from .event import SEQUENCE, TICK_EVENT_SEQUENCE, Event, TickEvent, TickEventType
from .item import Item, ItemType
from .memory import EntityType, Memory, MemoryPeriod, MemoryType, importance_of
from .player_character import PlayerCharacter
from .scene import Scene
from .scene_object import SceneObject, SceneObjectType
from .story_summary import StorySummary
from .world import World

# 统一导出所有领域模型，供 service / engine / graph 共享类型
# Re-export all domain models for shared use across service, engine and graph layers.
__all__ = [
    # 动作与决策 / Action and decision models
    "Action",
    "Actor",
    "Decision",
    # DM 与叙事 / DM and narrative models
    "DMRecord",
    "DomainModel",
    # 事件 / Event models
    "EntityType",
    "Event",
    "TickEvent",
    "TickEventType",
    "importance_of",
    # 物品 / Item models
    "Item",
    "ItemType",
    # 记忆 / Memory models
    "Memory",
    "MemoryPeriod",
    "MemoryType",
    # 角色与场景 / Character and scene models
    "PlayerCharacter",
    "Scene",
    "SceneObject",
    "SceneObjectType",
    # 序列与摘要 / Sequence and summary constants
    "SEQUENCE",
    "TICK_EVENT_SEQUENCE",
    # 故事与世界 / Story and world models
    "StorySummary",
    "World",
]

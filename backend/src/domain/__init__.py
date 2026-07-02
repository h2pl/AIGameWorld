"""AIGameWorld 领域模型层 / Domain layer.

所有模型继承 DomainModel（含 world_id），不再嵌套子模型。
All models inherit DomainModel (with world_id), no nested sub-models.
"""

from typing import Any

# 演员 NPC / Actor NPC model
from .actor import Actor

# 领域模型基类 / Domain model base class
from .base import DomainModel

# DM 产出记录 / DM output record (plot_brief + hints + narrative)
from .dm_record import DMRecord

# 事件模型 + 事件类型顺序 / Event model + type sequence
from .event import Event, SEQUENCE, TICK_EVENT_SEQUENCE, TickEvent

# 物品 / Item model
from .item import Item, ItemType

# 消息 / Message model
from .message import Message, TickMessage

# 玩家角色 / Player character model
from .player_character import PlayerCharacter

# 场景 / Scene model
from .scene import Scene

# 场景物体 / Scene object model
from .scene_object import SceneObject, SceneObjectType

# 剧情摘要 / Story summary model
from .story_summary import StorySummary

# 世界 / World model
from .world import World

# 兼容旧加载器的类型别名 / Compatibility aliases for legacy loaders
Attributes = dict[str, Any]
CharacterArc = dict[str, Any]
CombatStats = dict[str, Any]
Equipment = dict[str, Any]
InventorySlot = dict[str, Any]
Location = dict[str, Any]

__all__ = [
    "Actor",
    "Attributes",
    "CharacterArc",
    "CombatStats",
    "DMRecord",
    "DomainModel",
    "Equipment",
    "TickEvent",
    "Event",
    "InventorySlot",
    "Item",
    "ItemType",
    "Location",
    "TickMessage",
    "Message",
    "PlayerCharacter",
    "Scene",
    "SceneObject",
    "SceneObjectType",
    "SEQUENCE",
    "TICK_EVENT_SEQUENCE",
    "StorySummary",
    "World",
]

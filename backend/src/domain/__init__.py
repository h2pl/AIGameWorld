"""AIGameWorld 领域模型层——角色/物品/场景/故事/消息/世界 / Domain layer: chars, items, scenes, stories, messages, worlds."""

# ── 动作 / Action ──
# 导出所有子模块模型 / Re-export all sub-module models
from .action import Action
from .character import (
    Actor,
    Attributes,
    CharacterArc,
    CombatStats,
    Equipment,
    InventorySlot,
    Location,
    PlayerCharacter,
    Relationship,
)
from .dm_record import DMRecord
from .event import (
    SEQUENCE,
    CharacterExploreEvent,
    CharacterMoveEvent,
    CharacterTalkEvent,
    DmNarrativeEvent,
    Event,
    ExploreRoll,
    OpeningEvent,
    SceneObjectsEvent,
    SceneSetupEvent,
)
from .item import Item, ItemType
from .message import Message
from .scene_object import SceneObject, SceneObjectType
from .story import Quest
from .story_summary import StorySummary
from .world import World

# 公共 API / Public API
__all__ = [
    "Action",
    "Actor",
    "Attributes",
    "CharacterArc",
    "CharacterExploreEvent",
    "CharacterMoveEvent",
    "CharacterTalkEvent",
    "CombatStats",
    "DmNarrativeEvent",
    "DMRecord",
    "Equipment",
    "Event",
    "ExploreRoll",
    "InventorySlot",
    "Item",
    "ItemType",
    "Location",
    "Message",
    "OpeningEvent",
    "PlayerCharacter",
    "Quest",
    "Relationship",
    "SEQUENCE",
    "SceneObject",
    "SceneObjectType",
    "SceneObjectsEvent",
    "SceneSetupEvent",
    "StorySummary",
    "World",
]

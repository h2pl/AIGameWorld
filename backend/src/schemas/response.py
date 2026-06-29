"""Engine 输出 Schema / Response DTO"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from ..domain.action import Action
    from ..domain.event import Event
    from ..domain.instruction import DMInstruction


# ============================================================
# 公共基类 / Common base
# ============================================================
class EngineResponse(BaseModel):
    """所有 Engine 输出 DTO 的基类——统一 errors 字段 / Base response with errors."""

    model_config = ConfigDict(extra="forbid")

    errors: list[str] = Field(default_factory=list)


# ============================================================
# Phase 1 & 6: DM
# ============================================================
class DMCreateResponse(EngineResponse):
    instructions_out: list[str] = Field(default_factory=list)
    plot_brief: str = ""
    scene_direction: dict[str, Any] = {}

    @classmethod
    def from_entity(cls, dm: DMInstruction) -> DMCreateResponse:
        return cls(instructions_out=[dm.model_dump_json()])


class DMNarrateResponse(EngineResponse):
    narrative_out: str = ""
    branch_points: list[dict[str, Any]] = Field(default_factory=list)
    hooks_resolved: list[str] = Field(default_factory=list)


# ============================================================
# Phase 2: World
# ============================================================
class WorldUpdateResponse(EngineResponse):
    events_out: list[dict[str, Any]] = []

    @classmethod
    def from_entities(cls, events: list[Event]) -> WorldUpdateResponse:
        return cls(events_out=[e.model_dump() for e in events])


# ============================================================
# Phase 3: Character
# ============================================================
class PCDecideResponse(EngineResponse):
    character_id: str = ""
    type: str = ""
    description: str = ""

    @classmethod
    def from_entity(cls, action: Action) -> PCDecideResponse:
        return cls(
            character_id=action.character_id, type=action.action_type, description=action.reasoning
        )


class ActorDecideResponse(EngineResponse):
    character_id: str = ""
    type: str = ""
    description: str = ""

    @classmethod
    def from_entity(cls, action: Action) -> ActorDecideResponse:
        return cls(
            character_id=action.character_id, type=action.action_type, description=action.reasoning
        )


# ============================================================
# Phase 4: Engines
# ============================================================
class CombatResponse(EngineResponse):
    winner: str | None = None  # "party" | "enemy" | None
    rounds: int = 0
    survivors: list[dict[str, Any]] = []
    combat_log: list[dict[str, Any]] = []


class DialogueResponse(EngineResponse):
    success: bool | None = None
    content: str | None = None


class ExplorationResponse(EngineResponse):
    success: bool | None = None
    result: dict[str, Any] | None = None


# ============================================================
# Phase 4 continued: Quest
# ============================================================
class QuestResponse(EngineResponse):
    completed_ids: list[str] = []


# ============================================================
# Phase 7: Reflection + Summarizer
# ============================================================
class ReflectionResponse(EngineResponse):
    insights_out: list[dict[str, Any]] = []


class SummarizerResponse(EngineResponse):
    compressed: bool = False
    summary_text: str = ""


# ============================================================
# Domain: Story (M4+)
# ============================================================
class StoryAdvanceResponse(EngineResponse):
    arcs_updated: list[dict[str, Any]] = []
    hooks_resolved: list[str] = []
    quests_completed: list[dict[str, Any]] = []


# ============================================================
# Domain: Item / SceneObject / Character (M8+)
# ============================================================
class ItemResponse(BaseModel):
    id: str = ""
    name: str = ""
    item_type: str = ""
    rarity: str = "common"
    description: str = ""


class SceneObjectInteractResponse(BaseModel):
    success: bool | None = None
    result: dict[str, Any] | None = None


class CharacterResponse(BaseModel):
    id: str = ""
    name: str = ""
    character_type: str = "pc"
    attributes: dict[str, int] = {}
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    scene_id: str = ""
    alive: bool = True

"""Engine 输出 Schema / Response DTO"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..domain.action import Action
    from ..domain.event import Event
    from ..domain.instruction import DMInstruction


# === Phase 4: Quest ===
class QuestResponse(BaseModel):
    completed_ids: list[str] = []


# === Phase 7: Reflection + Summarizer ===
class ReflectionResponse(BaseModel):
    insights_out: list[dict[str, Any]] = []


class SummarizerResponse(BaseModel):
    compressed: bool = False
    summary_text: str = ""


# === Phase 1 & 6: DM ===
class DMCreateResponse(BaseModel):
    instructions_out: list[str] = Field(default_factory=list)
    plot_brief: str = ""
    scene_direction: dict[str, Any] = {}
    errors: list[str] = Field(default_factory=list)  # 降级/异常时写入 / written on fallback

    @classmethod
    def from_entity(cls, dm: DMInstruction) -> DMCreateResponse:
        return cls(instructions_out=[dm.model_dump_json()])


class DMNarrateResponse(BaseModel):
    narrative_out: str = ""
    branch_points: list[dict[str, Any]] = Field(default_factory=list)
    hooks_resolved: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)  # 降级/异常时写入 / written on fallback


# === Phase 2: World ===
class WorldUpdateResponse(BaseModel):
    events_out: list[dict[str, Any]] = []

    @classmethod
    def from_entities(cls, events: list[Event]) -> WorldUpdateResponse:
        return cls(events_out=[e.model_dump() for e in events])


# === Phase 3: Character ===
class PCDecideResponse(BaseModel):
    character_id: str = ""
    type: str = ""
    description: str = ""

    @classmethod
    def from_entity(cls, action: Action) -> PCDecideResponse:
        return cls(
            character_id=action.character_id, type=action.action_type, description=action.reasoning
        )


class ActorDecideResponse(BaseModel):
    character_id: str = ""
    type: str = ""
    description: str = ""

    @classmethod
    def from_entity(cls, action: Action) -> ActorDecideResponse:
        return cls(
            character_id=action.character_id, type=action.action_type, description=action.reasoning
        )


# === Phase 4: Engines ===
class CombatResponse(BaseModel):
    winner: str | None = None
    combat_log: list[dict[str, Any]] = []


class DialogueResponse(BaseModel):
    success: bool | None = None
    content: str | None = None


class ExplorationResponse(BaseModel):
    success: bool | None = None
    result: dict[str, Any] | None = None


# === Domain: Story (M4+) ===
class StoryAdvanceResponse(BaseModel):
    arcs_updated: list[dict[str, Any]] = []
    hooks_resolved: list[str] = []
    quests_completed: list[dict[str, Any]] = []


# === Domain: Item (M8+) ===
class ItemResponse(BaseModel):
    id: str = ""
    name: str = ""
    item_type: str = ""
    rarity: str = "common"
    description: str = ""


# === Domain: SceneObject (M8+) ===
class SceneObjectInteractResponse(BaseModel):
    success: bool | None = None
    result: dict[str, Any] | None = None


# === Domain: Character (Phase 3+) ===
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

"""Engine 输出 Schema / Response DTO"""
from __future__ import annotations
from typing import Any, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from ..domain.instruction import DMInstruction
    from ..domain.action import Action


# === Phase 1 & 6: DM ===
class DMCreateResponse(BaseModel):
    instructions_out: list[dict[str, Any]] = []
    plot_brief: str = ""
    scene_direction: dict[str, Any] = {}

    @classmethod
    def from_entity(cls, dm: DMInstruction) -> DMCreateResponse:
        return cls(instructions_out=[dm.model_dump()])


class DMNarrateResponse(BaseModel):
    narrative_out: str = ""


# === Phase 2: World ===
class WorldUpdateResponse(BaseModel):
    events_out: list[dict[str, Any]] = []


# === Phase 3: Character ===
class PCDecideResponse(BaseModel):
    character_id: str = ""
    type: str = ""
    description: str = ""

    @classmethod
    def from_entity(cls, action: Action) -> PCDecideResponse:
        return cls(
            character_id=action.character_id,
            type=action.action_type,
            description=action.reasoning,
        )


class ActorDecideResponse(BaseModel):
    character_id: str = ""
    type: str = ""
    description: str = ""

    @classmethod
    def from_entity(cls, action: Action) -> ActorDecideResponse:
        return cls(
            character_id=action.character_id,
            type=action.action_type,
            description=action.reasoning,
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

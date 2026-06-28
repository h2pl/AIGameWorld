"""Engine 输出 Schema / Response DTO"""
from typing import Any
from pydantic import BaseModel


# === Phase 1 & 6: DM ===
class DMCreateResponse(BaseModel):
    instructions_out: list[dict[str, Any]] = []
    plot_brief: str = ""
    scene_direction: dict[str, Any] = {}


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


class ActorDecideResponse(BaseModel):
    character_id: str = ""
    type: str = ""
    description: str = ""


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

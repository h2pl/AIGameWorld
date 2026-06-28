"""Engine 输入 Schema / Request DTO"""
from typing import Any
from pydantic import BaseModel


# === Phase 1 & 6: DM ===
class DMCreateRequest(BaseModel):
    tick: int = 0
    plot_brief: str = ""


class DMNarrateRequest(BaseModel):
    tick: int = 0
    plot_brief: str = ""
    dm_instructions: list[dict[str, Any]] = []
    scene_direction: dict[str, Any] = {}
    character_actions: list[dict[str, Any]] = []


# === Phase 2: World ===
class WorldUpdateRequest(BaseModel):
    tick: int = 0
    dm_instructions: list[dict[str, Any]] = []


# === Phase 3: Character ===
class PCDecideRequest(BaseModel):
    pc_id: str = ""
    plot_brief: str = ""
    tick: int = 0


class ActorDecideRequest(BaseModel):
    actor_id: str = ""
    plot_brief: str = ""
    tick: int = 0


# === Phase 4: Engines ===
class CombatRequest(BaseModel):
    participants: list[str] = []
    round: int = 1


class DialogueRequest(BaseModel):
    speaker: str = ""
    target: str = ""
    intent: str = ""


class ExplorationRequest(BaseModel):
    character_id: str = ""
    action_type: str = ""


class QuestRequest(BaseModel):
    quests: list[dict[str, Any]] = []
    event_log: list[dict[str, Any]] = []


# === Phase 7: Reflection ===
class ReflectionRequest(BaseModel):
    character_id: str = ""
    memories: list[dict[str, Any]] = []


class SummarizerRequest(BaseModel):
    events: list[dict[str, Any]] = []
    tick: int = 0

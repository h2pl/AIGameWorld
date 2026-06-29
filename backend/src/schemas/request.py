"""Engine 输入 Schema / Request DTO"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


# === Phase 1 & 6: DM ===
class DMCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick: int = 0
    plot_brief: str = ""


class DMNarrateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick: int = 0
    plot_brief: str = ""
    dm_instructions: list[str] = []
    scene_direction: dict[str, Any] = {}
    character_actions: list[dict[str, Any]] = []


# === Phase 2: World ===
class WorldUpdateRequest(BaseModel):
    tick: int = 0
    dm_instructions: list[str] = []


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
    model_config = ConfigDict(extra="forbid")

    character_id: str = ""
    character_name: str = ""
    character_type: str = "pc"  # "pc" | "actor"
    arc_stage: str = ""
    arc_description: str = ""
    memories: list[dict[str, Any]] = []
    recent_reflections: list[str] = []  # 历史反思洞见，防重复 / previous insights to avoid duplicates
    tick: int = 0


class SummarizerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[dict[str, Any]] = []
    character_count: int = 0
    tick: int = 0


# === Domain: Story (M4+) ===
class StoryAdvanceRequest(BaseModel):
    tick: int = 0
    narrative: str = ""
    character_actions: list[dict[str, Any]] = []


# === Domain: Item (M8+) ===
class ItemQueryRequest(BaseModel):
    item_id: str = ""


# === Domain: SceneObject (M8+) ===
class SceneObjectInteractRequest(BaseModel):
    object_id: str = ""
    character_id: str = ""
    action_type: str = ""


# === Domain: Character (Phase 3+) ===
class CharacterLoadRequest(BaseModel):
    character_id: str = ""

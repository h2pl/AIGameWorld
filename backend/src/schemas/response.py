"""Engine 输出 Schema / Response DTO"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    hints: list[str] = Field(default_factory=list)
    plot_brief: str = ""
    scene_id: str = ""


class DMNarrateResponse(EngineResponse):
    narrative_out: str = ""


# ============================================================
# Phase 2: World
# ============================================================
class SceneProcessResponse(EngineResponse):
    tick_events_out: list[dict[str, Any]] = []


# ============================================================
# Phase 3: Character
# ============================================================
class PCDecideResponse(EngineResponse):
    pc_id: str = ""
    type: str = ""
    description: str = ""


class SceneObservation(EngineResponse):
    pc_id: str = ""
    nearby_pc_ids: list[str] = Field(default_factory=list)
    nearby_actor_ids: list[str] = Field(default_factory=list)
    scene_object_ids: list[str] = Field(default_factory=list)


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

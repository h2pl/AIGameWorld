"""Engine 模型：各 Engine 的输入 / 输出"""
from typing import Any
from pydantic import BaseModel


class CombatInput(BaseModel):
    """Phase 4: 战斗裁决的 Engine 输入"""
    participants: list[str] = []
    round: int = 1


class CombatOutput(BaseModel):
    """Phase 4: 战斗裁决的 Engine 输出（M6 接入 DndRules）"""
    winner: str | None = None
    combat_log: list[dict[str, Any]] = []


class DialogueInput(BaseModel):
    """Phase 4: 对话检定的 Engine 输入"""
    speaker: str = ""
    target: str = ""
    intent: str = ""


class DialogueOutput(BaseModel):
    """Phase 4: 对话检定的 Engine 输出"""
    success: bool | None = None
    content: str | None = None


class ExplorationInput(BaseModel):
    """Phase 4: 探索检定的 Engine 输入"""
    character_id: str = ""
    action_type: str = ""


class ExplorationOutput(BaseModel):
    """Phase 4: 探索检定的 Engine 输出"""
    success: bool | None = None
    result: dict[str, Any] | None = None


class QuestInput(BaseModel):
    """Phase 4: 任务检查的 Engine 输入"""
    quests: list[dict[str, Any]] = []
    event_log: list[dict[str, Any]] = []

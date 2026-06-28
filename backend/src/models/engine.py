"""Engine 模型：各 Engine 的输入 / 输出类型"""
from typing import TypedDict, Any


class CombatInput(TypedDict):
    """Phase 4: 战斗裁决的 Engine 输入"""
    participants: list[str]
    round: int


class CombatOutput(TypedDict, total=False):
    """Phase 4: 战斗裁决的 Engine 输出"""
    winner: str
    combat_log: list[dict[str, Any]]


class DialogueInput(TypedDict):
    """Phase 4: 对话检定的 Engine 输入"""
    speaker: str
    target: str
    intent: str


class DialogueOutput(TypedDict, total=False):
    """Phase 4: 对话检定的 Engine 输出"""
    success: bool
    content: str


class ExplorationInput(TypedDict):
    """Phase 4: 探索检定的 Engine 输入"""
    character_id: str
    action_type: str


class ExplorationOutput(TypedDict, total=False):
    """Phase 4: 探索检定的 Engine 输出"""
    success: bool
    result: dict[str, Any]


class QuestInput(TypedDict):
    """Phase 4: 任务检查的 Engine 输入"""
    quests: list[dict[str, Any]]
    event_log: list[dict[str, Any]]


# check_quests returns list[str], no TypedDict needed

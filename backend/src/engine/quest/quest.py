"""Quest Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from typing import TypedDict, Any


class QuestInput(TypedDict):
    """Phase 4: 任务检查的 Engine 输入"""
    quests: list[dict[str, Any]]
    event_log: list[dict[str, Any]]


def check_quests(input: QuestInput) -> list[str]:
    """检查任务完成 / Check quest completion. Mock."""
    return []

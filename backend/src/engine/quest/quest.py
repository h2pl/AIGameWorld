"""Quest Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class QuestSubState(TypedDict):
    """Quest Service 内部数据契约 / Quest service internal data contract."""
    quests: list[dict[str, Any]]
    event_log: list[dict[str, Any]]
    completed_quests: list[str]


def check_quests(quests: list[dict[str, Any]], event_log: list[dict[str, Any]]) -> list[str]:
    """检查任务完成 / Check quest completion. Mock."""
    return []

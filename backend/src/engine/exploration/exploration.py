"""Exploration Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class ExplorationSubState(TypedDict):
    """Exploration Service 内部数据契约 / Exploration service internal data contract."""
    character_id: str
    action_type: str
    check_result: dict[str, Any]


def resolve_exploration(character_id: str, action_type: str) -> dict[str, Any]:
    """探索检定 / Exploration check. Mock."""
    return {}

"""Dialogue Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class DialogueSubState(TypedDict):
    """Dialogue Service 内部数据契约 / Dialogue service internal data contract."""
    speaker: str
    target: str
    intent: str
    check_result: dict[str, Any]


def resolve_dialogue(speaker: str, target: str, intent: str) -> dict[str, Any]:
    """对话检定 / Dialogue check. Mock."""
    return {}

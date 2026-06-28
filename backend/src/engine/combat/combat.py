"""Combat Service: 纯业务逻辑 / Pure business logic (Service layer)."""

from typing import TypedDict, Any


class CombatSubState(TypedDict):
    """Combat Service 内部数据契约 / Combat service internal data contract."""
    participants: list[str]
    round: int
    result: dict[str, Any] | None


def resolve_combat(participants: list[str], round: int) -> dict[str, Any] | None:
    """战斗裁决 / Combat resolution. Mock. M6 接入 DndRules."""
    return None

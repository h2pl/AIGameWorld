"""Combat Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from typing import TypedDict, Any


class CombatInput(TypedDict):
    """Phase 4: 战斗裁决的 Engine 输入"""
    participants: list[str]
    round: int


def resolve_combat(input: CombatInput) -> dict[str, Any] | None:
    """战斗裁决 / Combat resolution. Mock. M6 接入 DndRules."""
    return None

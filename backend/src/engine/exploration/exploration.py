"""Exploration Engine: 纯业务逻辑 / Pure business logic (Engine layer)."""

from typing import TypedDict, Any


class ExplorationInput(TypedDict):
    """Phase 4: 探索检定的 Engine 输入"""
    character_id: str
    action_type: str


def resolve_exploration(input: ExplorationInput) -> dict[str, Any]:
    """探索检定 / Exploration check. Mock."""
    return {}

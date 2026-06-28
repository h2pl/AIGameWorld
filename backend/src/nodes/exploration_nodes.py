"""Exploration Node: State <-> Service glue / 探索节点：State ↔ Service 胶水。"""
from typing import Any
from ..engine.exploration.exploration import resolve_exploration


def exploration_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 4: 探索检定 / Exploration check.

    产出 / Outputs: check_result
    """
    result = resolve_exploration(
        character_id=state.get("character_id", ""),
        action_type=state.get("action_type", ""),
    )
    return {"check_result": result}

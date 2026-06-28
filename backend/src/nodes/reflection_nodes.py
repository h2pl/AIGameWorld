"""Reflection Node: State <-> Service glue / 反思节点：State ↔ Service 胶水。"""
from typing import Any
from ..engine.reflection.reflection import reflect


def reflection_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 7: 角色反思 / Character reflection.

    产出 / Outputs: insight_out
    """
    insight = reflect(
        character_id=state.get("character_id", ""),
        memories=state.get("memories", []),
    )
    return {"insight_out": insight}

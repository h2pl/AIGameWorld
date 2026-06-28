"""Reflection Service: State ↔ Engine adapter / 反思服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.reflection.reflection import reflect as _reflect
from ..graph.state import ReflectionSubState


def reflect(state: ReflectionSubState) -> dict[str, Any]:
    """Phase 7: 角色反思 / Character reflection.

    产出 / Outputs: reflected_characters
    """
    _reflect(
        character_id=state.get("character_id", ""),
        memories=state.get("memories", []),
    )
    return {"reflected_characters": []}

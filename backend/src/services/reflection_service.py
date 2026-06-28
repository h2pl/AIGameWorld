"""Reflection Service: State ↔ Engine adapter / 反思服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.reflection.reflection import reflect as _reflect
from ..graph.state import ReflectionSubState


def _to_reflection_input(state: ReflectionSubState) -> dict[str, Any]:
    """① State → Engine 输入"""
    return {
        "character_id": state.get("character_id", ""),
        "memories": state.get("memories", []),
    }


def reflect(state: ReflectionSubState) -> dict[str, Any]:
    """Phase 7: 角色反思 / Character reflection.

    ① State → Engine 输入
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: reflected_characters
    """
    engine_input = _to_reflection_input(state)  # ①
    _reflect(**engine_input)                     # ②
    return {"reflected_characters": []}           # ③


"""Reflection Service: State ↔ Engine adapter."""
from typing import Any
from ..models.reflection import ReflectionInput
from ..engine.reflection.reflection import reflect as _reflect
from ..graph.state import ReflectionSubState


def _to_reflection_input(state: ReflectionSubState) -> ReflectionInput:
    return {"character_id": state.get("character_id", ""), "memories": state.get("memories", [])}


def reflect(state: ReflectionSubState) -> dict[str, Any]:
    """Phase 7: 角色反思. 产出 / Outputs: reflected_characters"""
    _reflect(_to_reflection_input(state))
    return {"reflected_characters": []}

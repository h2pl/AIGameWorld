"""Reflection Service: State ↔ Engine adapter."""
from typing import Any
from ..schemas.request import ReflectionRequest
from ..engine.reflection.reflection import reflect as _reflect
from ..graph.state import ReflectionSubState


def reflect(state: ReflectionSubState) -> dict[str, Any]:
    """Phase 7: 角色反思."""
    _reflect(ReflectionRequest(
        character_id=state.get("character_id", ""),
        memories=state.get("memories", []),
    ))
    return {"reflected_characters": []}

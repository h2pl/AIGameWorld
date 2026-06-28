"""Reflection Service: State ↔ Engine adapter."""

from ..schemas.request import ReflectionRequest
from ..engine.reflection import reflection as reflection_engine
from ..graph.state import ReflectionSubState


def reflect(state: ReflectionSubState) -> dict:
    """Phase 7: 角色反思."""
    result = reflection_engine.reflect(ReflectionRequest(
        character_id=state.get("character_id", ""),
        memories=state.get("memories", []),
    ))
    return {"reflected_characters": result.model_dump().get("insights_out", [])}

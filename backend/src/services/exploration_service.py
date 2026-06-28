"""Exploration Service: State ↔ Engine adapter."""
from typing import Any
from ..models.io.engine import ExplorationInput
from ..engine.exploration.exploration import resolve_exploration as _resolve_exploration
from ..graph.state import EngineSubState


def exploration(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 探索检定."""
    result = _resolve_exploration(ExplorationInput(
        character_id=state.get("character_id", ""),
        action_type=state.get("action_type", ""),
    ))
    return {"engine_results": [{"engine": "exploration", "result": result}]}

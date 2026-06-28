"""Exploration Service: State ↔ Engine adapter."""

from ..schemas.request import ExplorationRequest
from ..engine.exploration import exploration as exploration_engine
from ..graph.state import EngineSubState


def exploration(state: EngineSubState) -> dict:
    """Phase 4: 探索检定."""
    result = exploration_engine.resolve_exploration(ExplorationRequest(
        character_id=state.get("character_id", ""),
        action_type=state.get("action_type", ""),
    ))
    return {"engine_results": [{"engine": "exploration", "result": result.model_dump()}]}

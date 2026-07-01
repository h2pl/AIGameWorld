"""Exploration Service: State ↔ Engine adapter."""
import logging

from ..engine.exploration import exploration as exploration_engine
from ..graph.state import EngineSubState
from ..schemas.request import ExplorationRequest


def exploration(state: EngineSubState) -> dict:
    logging.getLogger("aw.svc").info("[exploration]")
    """Phase 4: 探索检定."""
    result = exploration_engine.resolve_exploration(
        ExplorationRequest(
            character_id=state.get("character_id", ""),
            action_type=state.get("action_type", ""),
        )
    )
    return {"engine_results": [{"engine": "exploration", "result": result.model_dump()}]}

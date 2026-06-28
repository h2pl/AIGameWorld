"""Exploration Service: State ↔ Engine adapter."""
from typing import Any
from ..models.engine import ExplorationInput
from ..engine.exploration.exploration import resolve_exploration as _resolve_exploration
from ..graph.state import EngineSubState


def _to_exploration_input(state: EngineSubState) -> ExplorationInput:
    return {"character_id": state.get("character_id", ""), "action_type": state.get("action_type", "")}


def exploration(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 探索检定. 产出 / Outputs: engine_results"""
    result = _resolve_exploration(_to_exploration_input(state))
    return {"engine_results": [{"engine": "exploration", "result": result}]}

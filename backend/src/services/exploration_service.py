"""Exploration Service: State ↔ Engine adapter / 探索服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.exploration.exploration import resolve_exploration as _resolve_exploration
from ..graph.state import EngineSubState


def exploration(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 探索检定 / Exploration check.

    产出 / Outputs: engine_results
    """
    result = _resolve_exploration(
        character_id=state.get("character_id", ""),
        action_type=state.get("action_type", ""),
    )
    return {"engine_results": [{"engine": "exploration", "result": result}]}

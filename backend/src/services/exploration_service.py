"""Exploration Service: State ↔ Engine adapter / 探索服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.exploration.exploration import ExplorationInput, resolve_exploration as _resolve_exploration
from ..graph.state import EngineSubState


def _to_exploration_input(state: EngineSubState) -> ExplorationInput:
    """① State → Engine 输入"""
    return {
        "character_id": state.get("character_id", ""),
        "action_type": state.get("action_type", ""),
    }


def exploration(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 探索检定 / Exploration check.

    ① State → ExplorationInput
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: engine_results
    """
    engine_input = _to_exploration_input(state)                      # ①
    result = _resolve_exploration(engine_input)                      # ②
    return {"engine_results": [{"engine": "exploration", "result": result}]}  # ③

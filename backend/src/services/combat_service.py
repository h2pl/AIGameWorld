"""Combat Service: State ↔ Engine adapter / 战斗服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.combat.combat import resolve_combat as _resolve_combat
from ..graph.state import EngineSubState


def _to_combat_input(state: EngineSubState) -> dict[str, Any]:
    """① State → Engine 输入"""
    return {
        "participants": state.get("participants", []),
        "round": state.get("round", 1),
    }


def combat(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 战斗裁决 / Combat resolution.

    ① State → Engine 输入
    ② 调用 Engine
    ③ 映射回 State key
    产出 / Outputs: engine_results, combat_result
    """
    engine_input = _to_combat_input(state)                       # ①
    result = _resolve_combat(**engine_input)                      # ②
    return {                                                      # ③
        "engine_results": [{"engine": "combat", "result": result}],
        "combat_result": result,
    }


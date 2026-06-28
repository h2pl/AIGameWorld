"""Combat Service: State ↔ Engine adapter / 战斗服务：State ↔ Engine 适配。"""
from typing import Any
from ..engine.combat.combat import resolve_combat as _resolve_combat
from ..graph.state import EngineSubState


def combat(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 战斗裁决 / Combat resolution.

    产出 / Outputs: engine_results, combat_result
    """
    result = _resolve_combat(
        participants=state.get("participants", []),
        round=state.get("round", 1),
    )
    return {
        "engine_results": [{"engine": "combat", "result": result}],
        "combat_result": result,
    }

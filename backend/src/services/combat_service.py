"""Combat Service: State ↔ Engine adapter."""
from typing import Any
from ..models.engine import CombatInput
from ..engine.combat.combat import resolve_combat as _resolve_combat
from ..graph.state import EngineSubState


def _to_combat_input(state: EngineSubState) -> CombatInput:
    return {"participants": state.get("participants", []), "round": state.get("round", 1)}


def combat(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 战斗裁决. 产出 / Outputs: engine_results, combat_result"""
    result = _resolve_combat(_to_combat_input(state))
    return {"engine_results": [{"engine": "combat", "result": result}], "combat_result": result}

"""Combat Service: State ↔ Engine adapter."""
from typing import Any
from ..models.io.engine import CombatInput
from ..engine.combat.combat import resolve_combat as _resolve_combat
from ..graph.state import EngineSubState


def combat(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 战斗裁决."""
    result = _resolve_combat(CombatInput(
        participants=state.get("participants", []),
        round=state.get("round", 1),
    ))
    return {"engine_results": [{"engine": "combat", "result": result}], "combat_result": result}

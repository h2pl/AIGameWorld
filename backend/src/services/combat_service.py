"""Combat Service: State ↔ Engine adapter."""
from typing import Any
from ..schemas.request import CombatRequest
from ..engine.combat.combat import resolve_combat as _resolve_combat
from ..graph.state import EngineSubState


def combat(state: EngineSubState) -> dict[str, Any]:
    """Phase 4: 战斗裁决."""
    result = _resolve_combat(CombatRequest(
        participants=state.get("participants", []),
        round=state.get("round", 1),
    ))
    return {"engine_results": [{"engine": "combat", "result": result}], "combat_result": result}

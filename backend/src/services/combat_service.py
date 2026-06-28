"""Combat Service: State ↔ Engine adapter."""

from ..schemas.request import CombatRequest
from ..engine.combat import combat as combat_engine
from ..graph.state import EngineSubState


def combat(state: EngineSubState) -> dict:
    """Phase 4: 战斗裁决."""
    result = combat_engine.resolve_combat(CombatRequest(
        participants=state.get("participants", []),
        round=state.get("round", 1),
    ))
    return {"engine_results": [{"engine": "combat", "result": result.model_dump()}], "combat_result": result.model_dump()}

"""Combat Service: State ↔ Engine adapter."""

from ..engine.combat import combat_engine
from ..graph.state import EngineSubState
from ..schemas.request import CombatParticipant, CombatRequest
from ..utils.logging import get_logger


def combat(state: EngineSubState) -> dict:
    get_logger(__name__).info("[combat]")
    """Phase 4: 战斗裁决 / Combat resolution."""
    raw = state.get("participants", [])
    if raw and isinstance(raw[0], str):
        # 旧格式兼容：["hero", "goblin"] → 默认 party/enemy
        participants = [
            CombatParticipant(name=p, team="party" if i == 0 else "enemy")
            for i, p in enumerate(raw)
        ]
    else:
        participants = raw

    result = combat_engine.resolve_combat(
        CombatRequest(participants=participants, round=state.get("round", 1))
    )
    return {
        "engine_results": [{"engine": "combat", "result": result.model_dump()}],
        "combat_result": result.model_dump(),
    }

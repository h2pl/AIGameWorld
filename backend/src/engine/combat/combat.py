"""Combat Engine: 纯业务逻辑."""

from ...schemas.request import CombatRequest
from ...schemas.response import CombatResponse


def resolve_combat(req: CombatRequest) -> CombatResponse:
    """战斗裁决. Mock. Phase 5 接入 D20 规则."""
    if not req.participants:
        return CombatResponse()
    return CombatResponse(
        winner=req.participants[0],
        combat_log=[{"round": 1, "action": "mock_skirmish"}],
    )

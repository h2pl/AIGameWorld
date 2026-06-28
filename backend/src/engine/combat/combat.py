"""Combat Engine: 纯业务逻辑."""

from ...schemas.request import CombatRequest
from ...schemas.response import CombatResponse


def resolve_combat(req: CombatRequest) -> CombatResponse:
    """战斗裁决. Mock. M6 接入 DndRules."""
    return CombatResponse()

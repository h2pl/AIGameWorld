"""PC Decide Engine: 纯业务逻辑."""

from ...schemas.request import PCDecideRequest
from ...schemas.response import PCDecideResponse


_DEMO_ACTIONS = {
    "alex": ("explore", "Alex scans the room for clues."),
    "maya": ("social", "Maya attempts to charm the innkeeper."),
    "garret": ("combat", "Garret draws his blade, ready for trouble."),
}


def pc_decide(req: PCDecideRequest) -> PCDecideResponse:
    """Phase 3: 单个 PC 决策. Mock. Phase 3 接入 LLM."""
    action_type, description = _DEMO_ACTIONS.get(
        req.pc_id, ("idle", f"{req.pc_id} waits patiently.")
    )
    return PCDecideResponse(
        character_id=req.pc_id,
        type=action_type,
        description=description,
    )

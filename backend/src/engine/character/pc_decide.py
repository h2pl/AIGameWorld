"""PC Engine: 纯业务逻辑."""

from ...schemas.request import PCDecideRequest
from ...schemas.response import PCDecideResponse
from ...domain.action import Action


def pc_decide(req: PCDecideRequest) -> PCDecideResponse:
    """Phase 3: PC 决策. Mock. M5 接入 LLM."""
    action = Action(
        character_id=req.pc_id,
        character_type="pc",
        tick=req.tick,
        action_type="explore",
        reasoning=f"PC {req.pc_id} deciding based on: {req.plot_brief}",
    )
    return PCDecideResponse.from_entity(action)

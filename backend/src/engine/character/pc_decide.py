"""PC Engine: 纯业务逻辑."""

from ...schemas.request import PCDecideRequest
from ...schemas.response import PCDecideResponse


def pc_decide(req: PCDecideRequest) -> PCDecideResponse:
    """Phase 3: PC 决策. Mock. M5 接入 LLM."""
    return PCDecideResponse(
        character_id=req.pc_id,
        type="explore",
        description="Looking around the area.",
    )

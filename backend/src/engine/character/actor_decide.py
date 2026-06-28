"""Actor Engine: 纯业务逻辑."""

from ...schemas.request import ActorDecideRequest
from ...schemas.response import ActorDecideResponse


def actor_decide(req: ActorDecideRequest) -> ActorDecideResponse:
    """Phase 3: Actor 决策. Mock. M5 接入 LLM."""
    return ActorDecideResponse(
        character_id=req.actor_id,
        type="idle",
        description="Going about daily business.",
    )

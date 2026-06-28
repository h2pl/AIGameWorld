"""Actor Engine: 纯业务逻辑."""

from ...schemas.request import ActorDecideRequest
from ...schemas.response import ActorDecideResponse
from ...domain.action import Action


def actor_decide(req: ActorDecideRequest) -> ActorDecideResponse:
    """Phase 3: Actor 决策. Mock. M5 接入 LLM."""
    action = Action(
        character_id=req.actor_id,
        character_type="actor",
        tick=req.tick,
        action_type="idle",
        reasoning=f"Actor {req.actor_id} deciding based on: {req.plot_brief}",
    )
    return ActorDecideResponse.from_entity(action)

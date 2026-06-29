"""Actor Decide Engine: 纯业务逻辑."""

from ...schemas.request import ActorDecideRequest
from ...schemas.response import ActorDecideResponse

_DEMO_ACTIONS = {
    "innkeeper": ("social", "The innkeeper wipes a mug and nods."),
    "guard": ("idle", "The guard stands watch at the door."),
    "goblin": ("combat", "The goblin snarls and lunges forward!"),
}


def actor_decide(req: ActorDecideRequest) -> ActorDecideResponse:
    """Phase 3: 单个 Actor 决策. Mock. Phase 3 接入 LLM."""
    action_type, description = _DEMO_ACTIONS.get(
        req.actor_id, ("idle", f"{req.actor_id} goes about their business.")
    )
    return ActorDecideResponse(
        character_id=req.actor_id,
        type=action_type,
        description=description,
    )

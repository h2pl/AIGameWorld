"""Actor Engine: 纯业务逻辑."""

from ...schemas.request import ActorDecideRequest
from ...schemas.response import ActorDecideResponse
from ...domain.entities.action import Action


def actor_decide(req: ActorDecideRequest) -> ActorDecideResponse:
    """Phase 3: Actor 决策. Mock. M5 接入 LLM.

    ① Request → Domain  ② 业务逻辑  ③ Domain → Response
    """
    action = Action.from_actor_request(req)
    return action.to_actor_response()

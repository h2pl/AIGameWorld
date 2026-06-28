"""PC Engine: 纯业务逻辑."""

from ...schemas.request import PCDecideRequest
from ...schemas.response import PCDecideResponse
from ...domain.entities.action import Action


def pc_decide(req: PCDecideRequest) -> PCDecideResponse:
    """Phase 3: PC 决策. Mock. M5 接入 LLM.

    ① Request → Domain  ② 业务逻辑  ③ Domain → Response
    """
    action = Action.from_pc_request(req)
    return action.to_pc_response()

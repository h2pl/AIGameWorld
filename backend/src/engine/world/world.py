"""World Engine: 纯业务逻辑."""

from ...schemas.request import WorldUpdateRequest
from ...schemas.response import WorldUpdateResponse


def execute_instructions(req: WorldUpdateRequest) -> WorldUpdateResponse:
    """执行 DM 指令. Mock. M6 接入场景实例化."""
    return WorldUpdateResponse()

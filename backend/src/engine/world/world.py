"""World Engine: 纯业务逻辑."""

from ...schemas.request import WorldUpdateRequest
from ...schemas.response import WorldUpdateResponse


def execute_instructions(req: WorldUpdateRequest) -> WorldUpdateResponse:
    """Phase 2: 执行 DM 指令. Mock. Phase 4 接入事件系统."""
    events = [
        {"type": "dm_instruction", "tick": req.tick, "description": inst}
        for inst in req.dm_instructions
    ]
    return WorldUpdateResponse(events_out=events)

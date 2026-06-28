"""World Engine: 纯业务逻辑."""

from ...schemas.request import WorldUpdateRequest
from ...schemas.response import WorldUpdateResponse


def execute_instructions(req: WorldUpdateRequest) -> WorldUpdateResponse:
    """Phase 2: 执行 DM 指令. Mock. Phase 4 接入事件系统."""
    events = []
    for inst in req.dm_instructions:
        inst_type = inst.get("type", "unknown")
        if inst_type == "scene_direction":
            events.append({
                "type": "set_dressing",
                "tick": req.tick,
                "description": f"Scene set: {inst.get('description', '')}",
                "featured_pcs": inst.get("featured_pcs", []),
                "featured_actors": inst.get("featured_actors", []),
            })
    return WorldUpdateResponse(events_out=events)

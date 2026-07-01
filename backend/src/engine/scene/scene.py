"""Scene Engine——场景与场景物品处理 / Scene & scene objects processing.

Phase 2: 接收 DM 指令，产出 scene_setup + scene_objects 事件。
"""

import logging

from ...schemas.request import WorldUpdateRequest
from ...schemas.response import WorldUpdateResponse


def process_scene(req: WorldUpdateRequest) -> WorldUpdateResponse:
    """处理 DM 指令，生成场景事件."""
    logging.getLogger("aw.eng").info("[scene]")
    events = [
        {"type": "dm_instruction", "tick": req.tick, "description": inst}
        for inst in req.dm_instructions
    ]
    return WorldUpdateResponse(events=events)

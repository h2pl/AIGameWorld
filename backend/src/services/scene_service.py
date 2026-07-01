"""Scene Service: State ↔ Engine adapter."""

import logging

from ..engine.scene import scene as scene_engine
from ..graph.state import OverallState
from ..schemas.request import SceneProcessRequest


def process_scene(state: OverallState) -> dict:
    """Phase 2: Scene Engine 处理 DM 指令生成场景事件."""
    logging.getLogger("aw.svc").info("[scene]")
    result = scene_engine.process_scene(
        SceneProcessRequest(
            tick=state.get("tick", 0),
            dm_instructions=state.get("dm_instructions", []),
        )
    )
    return {"scene_events": result.events}

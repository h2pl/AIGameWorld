"""Scene Service: State ↔ Engine adapter."""

import logging

from ..engine.scene import scene_engine
from ..graph.state import OverallState
from ..schemas.request import SceneProcessRequest

logger = logging.getLogger("aw.svc")


async def process_scene(state: OverallState, config=None) -> dict:
    """Phase 1.5: 场景引擎——写 scene_setup + scene_objects 事件到 tick_events 表."""
    tick = state.get("tick", 0)
    scene_id = state.get("scene_id", "")
    tick_message_id = state.get("tick_message_id", "")
    logger.info("[scene] tick=%s scene_id=%s tick_message_id=%s", tick, scene_id, tick_message_id)
    req = SceneProcessRequest(
        tick=tick, world_id=state.get("world_id", ""), scene_id=scene_id, tick_message_id=tick_message_id
    )
    await scene_engine.process_scene_setup(req, config=config)
    await scene_engine.process_scene_objects(req, config=config)
    return {}

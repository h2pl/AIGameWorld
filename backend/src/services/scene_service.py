"""Scene Service: State ↔ Engine adapter."""

import logging

from ..engine.scene import scene_engine
from ..graph.state import OverallState
from ..schemas.request import SceneProcessRequest

logger = logging.getLogger("aw.svc")


async def process_scene(state: OverallState, config=None) -> dict:
    """Phase 1.5: 场景引擎——写 scene_setup + scene_objects 事件到 events 表."""
    tick = state.get("tick", 0)
    scene_id = state.get("scene_id", "")
    msg_id = state.get("msg_id", "")
    logger.info("[scene] tick=%s scene_id=%s msg_id=%s", tick, scene_id, msg_id)
    req = SceneProcessRequest(
        tick=tick, world_id=state.get("world_id", ""), scene_id=scene_id, msg_id=msg_id
    )
    await scene_engine.process_scene_setup(req, config=config)
    await scene_engine.process_scene_objects(req, config=config)
    return {}

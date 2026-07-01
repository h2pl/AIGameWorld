"""Scene Engine——加载场景数据 + 构造事件 + 写入 events 表.

Phase 1.5: DM 已选出 scene_id，引擎从 DB 加载场景详情，分两步写入:
  - process_scene_setup: 写 scene_setup 事件
  - process_scene_objects: 写 scene_objects 事件（每个物体一条）
"""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...schemas.request import SceneProcessRequest
from ...utils.helpers import get_repo

logger = logging.getLogger("aw.eng")


async def process_scene_setup(req: SceneProcessRequest, config: RunnableConfig = None) -> None:
    """写入 scene_setup 事件."""
    scene_id = req.scene_id
    if not scene_id or not req.msg_id:
        return
    event_repo = get_repo(config, "event")
    if not event_repo:
        return
    await event_repo.insert_events(
        req.msg_id,
        req.tick,
        [
            {
                "type": "scene_setup",
                "tick": req.tick,
                "scene_id": scene_id,
                "description": "进入场景",
            }
        ],
    )
    logger.info("[scene] scene_setup tick=%s scene_id=%s", req.tick, scene_id)


async def process_scene_objects(req: SceneProcessRequest, config: RunnableConfig = None) -> None:
    """写入 scene_objects 事件（每个场景物体一条）."""
    scene_id = req.scene_id
    if not scene_id or not req.msg_id:
        return
    scene_repo = get_repo(config, "scene")
    if not scene_repo:
        return
    obj_ids = await scene_repo.get_object_ids(scene_id)
    if not obj_ids:
        return
    all_objs = await scene_repo.load_all()
    events: list[dict] = []
    for oid in obj_ids:
        if oid not in all_objs:
            continue
        obj = all_objs[oid]
        events.append(
            {
                "type": "scene_objects",
                "tick": req.tick,
                "scene_id": scene_id,
                "object_id": oid,
                "name": obj.name,
                "object_type": obj.object_type.value,
                "description": f"{obj.object_type.value}「{oid}」",
            }
        )
    if not events:
        return
    event_repo = get_repo(config, "event")
    if not event_repo:
        return
    await event_repo.insert_events(req.msg_id, req.tick, events)
    logger.info(
        "[scene] scene_objects tick=%s scene_id=%s count=%d", req.tick, scene_id, len(events)
    )

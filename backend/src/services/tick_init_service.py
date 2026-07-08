"""Tick Init Service: tick 初始化时的业务逻辑，不含 DB 读写。

负责 PC 出生点坐标分配 + 构建 tick 初始事件（dm_create → scene_setup）。
"""

from ..domain.event import TickEvent, TickEventType
from ..graph.state import OverallState
from ..utils.helpers import assign_spawn_positions
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("tick_init.assign_positions")
async def assign_pc_positions(state: OverallState, config=None) -> dict:
    """为未设置坐标的 PC 分配到场景出生点附近."""
    scene = state.get("scene")
    if scene is None:
        return {}
    scene_id = scene.id
    actors = state.get("actors", {})
    pcs = state.get("pcs", {})

    if not pcs or not scene_id:
        return {"pcs": pcs}

    unset = [
        pc for pc in pcs.values()
        if (pc.position_x == 0 and pc.position_y == 0) or pc.scene_id != scene_id
    ]
    if not unset:
        return {"pcs": pcs}

    assign_spawn_positions(unset, scene, actors)
    for pc in pcs.values():
        pc.scene_id = scene_id

    return {"pcs": pcs}


@trace_node("tick_init.dm_create_event")
async def build_dm_create_event(state: OverallState, config=None) -> dict:
    """构建 dm_create 事件——tick 的第一个事件."""
    dm = state.get("dm_record")
    if dm is None:
        return {}
    scene_id = dm.scene_id
    if not scene_id:
        return {}
    event = TickEvent(
        type=TickEventType.DM_CREATE,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene_id,
            "plot_brief": dm.plot_brief if dm else "",
            "hints": dm.hints if dm else [],
        },
    )
    prev = list(state.get("tick_events", []))
    return {"tick_events": [*prev, event]}


@trace_node("tick_init.scene_setup_event")
async def build_scene_setup_event(state: OverallState, config=None) -> dict:
    """构建 scene_setup 事件——此时 PC 坐标为起始坐标，未被 action 更新."""
    scene = state.get("scene")
    if scene is None:
        return {}
    scene_id = scene.id
    if not scene_id:
        return {}

    pcs = [pc.model_dump() for pc in state.get("pcs", {}).values()]
    actors = [actor.model_dump() for actor in state.get("actors", {}).values()]
    scene_objects = state.get("scene_objects", [])

    event = TickEvent(
        type=TickEventType.SCENE_SETUP,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene_id,
            "scene": scene.model_dump(),
            "pcs": pcs,
            "actors": actors,
            "scene_objects": [obj.model_dump() for obj in scene_objects],
        },
    )
    prev = list(state.get("tick_events", []))
    return {"tick_events": [*prev, event]}

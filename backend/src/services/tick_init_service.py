"""Tick Init Service: 每个 tick 都执行一次的初始化逻辑 / Per-tick initialization.

语义边界（与 world_init / party 区分）：
  - world_init_service  ：整个世界只执行一次的初始化（世界/场景确定、Neo4j 节点），
                          由 orchestrator.run_tick 在每 tick 入口前调用 ensure_world_initialized
                          幂等完成，完全在 tick 主图之外，不属于任何一个 tick 内部。
  - party_service       ：每个 tick 都执行的团体协同（集体讨论、集体决策切场景）
  - tick_init_service   ：每个 tick 都执行的纯初始化，不依赖团体决策结果：
      * assign_pc_positions      —— PC 出生点坐标分配
      * build_dm_create_event    —— 构造本 tick 首个事件（DM_CREATE）
      * save_scene_setup_snapshot —— 截屏 scene/pcs/actors/scene_objects，供 flush_events 构建 scene_setup

注意：本模块不再包含 world_init 或 party（团体决策）逻辑。
"""

from ..domain.event import TickEvent, TickEventType
from ..graph.state import OverallState
from ..utils.helpers import assign_spawn_positions
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("tick_init.assign_positions")
async def assign_pc_positions(state: OverallState, config=None) -> dict:
    """为未设置坐标的 PC 分配到场景出生点附近 / Per-tick: assign PC spawn positions."""
    scene = state.get("scene")
    if scene is None:
        return {}
    scene_id = scene.id
    actors = state.get("actors", {})
    pcs = state.get("pcs", {})

    if not pcs or not scene_id:
        return {"pcs": pcs}

    unset = [
        pc
        for pc in pcs.values()
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
    """构建场景设定事件——tick 的第一个事件（场景由 world_init / party.decide_scene 决定，不再依赖 DM）.

    payload 携带 current_scene_id；plot_brief/hints 由后续 dm_service.dm_create 引擎产出，
    此处 DM_CREATE 事件只携带场景 id（空壳），供前端在建场时定位场景。
    """
    scene_id = state.get("current_scene_id", "")
    if not scene_id:
        return {}
    event = TickEvent(
        type=TickEventType.DM_CREATE,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": scene_id,
            "plot_brief": "",
            "hints": [],
        },
    )
    prev = list(state.get("tick_events", []))
    return {"tick_events": [*prev, event]}


@trace_node("tick_init.scene_setup_snapshot")
async def save_scene_setup_snapshot(state: OverallState, config=None) -> dict:
    """截屏 scene/pcs/actors/scene_objects，供 flush_events 构建 scene_setup / Per-tick snapshot."""
    scene = state.get("scene")
    if scene is None:
        return {}
    pcs = {pc_id: pc.model_dump() for pc_id, pc in state.get("pcs", {}).items()}
    actors = {actor_id: actor.model_dump() for actor_id, actor in state.get("actors", {}).items()}
    scene_objects = [obj.model_dump() for obj in state.get("scene_objects", [])]
    return {
        "pcs_snapshot": {
            "scene": scene.model_dump(),
            "pcs": pcs,
            "actors": actors,
            "scene_objects": scene_objects,
        },
    }

"""Tick Init Service: tick 初始化时的业务逻辑，不含 DB 读写。

负责 PC 出生点坐标分配 + 构建 tick 初始事件（dm_create → scene_setup）。
"""

from ..domain.event import TickEvent, TickEventType
from ..graph.state import OverallState
from ..utils.helpers import assign_spawn_positions, get_repo
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("tick_init.init_graph_db")
async def init_graph_db(state: OverallState, config=None) -> dict:
    """初始化图数据库（仅在 tick=1 时执行）."""
    if state.get("tick", 0) != 1:
        return {}

    pcs = state.get("pcs", {})
    if not pcs:
        return {}

    neo4j_repo = get_repo(config, "neo4j")
    if not neo4j_repo:
        logger.warning("[tick_init] Neo4j unavailable, skipping graph init")
        return {}

    # 初始化 PC 节点
    for pc in pcs.values():
        await neo4j_repo.merge_node(
            label="Actor", properties={"id": pc.id, "name": pc.name, "type": "pc"}
        )

    # 建立主角团内部的友军关系 (PARTY_MEMBER)
    tick = state.get("tick", 1)
    for pc1 in pcs.values():
        for pc2 in pcs.values():
            if pc1.id != pc2.id:
                await neo4j_repo.merge_relationship(
                    start_label="Actor",
                    start_key="id",
                    start_val=pc1.id,
                    end_label="Actor",
                    end_key="id",
                    end_val=pc2.id,
                    rel_type="PARTY_MEMBER",
                    tick=tick,
                )
    return {}


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


@trace_node("tick_init.scene_setup_snapshot")
async def save_scene_setup_snapshot(state: OverallState, config=None) -> dict:
    """截屏 scene/pcs/actors/scene_objects，供 flush_events 构建 scene_setup."""
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

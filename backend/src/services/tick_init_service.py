"""Tick Init Service: tick 初始化时的业务逻辑，不含 DB 读写。

当前仅负责 PC 出生点坐标分配——委托 helpers.assign_spawn_positions 完成。
"""

from ..graph.state import OverallState
from ..utils.helpers import assign_spawn_positions
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("tick_init.assign_positions")
async def assign_pc_positions(state: OverallState, config=None) -> dict:
    """为未设置坐标的 PC 分配到场景出生点附近."""
    scene_id = state.get("scene_id", "")
    scene = state.get("scene")
    actors = state.get("actors", {})
    pcs = state.get("pcs", {})

    if not pcs or not scene_id or scene is None:
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

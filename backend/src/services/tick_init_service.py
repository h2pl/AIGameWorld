"""Tick Init Service: tick 初始化时的业务逻辑，不含 DB 读写。

当前仅负责 PC 出生点坐标分配——从 state 中读取已加载的 PC/Scene/Actor，
按出生点螺旋搜索分配坐标，避开实体占用和地图碰撞。
"""

from ..domain import Actor, PlayerCharacter, Scene
from ..graph.state import OverallState
from ..utils.helpers import build_occupied, find_vacant, load_blocked_tiles
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("tick_init.assign_positions")
async def assign_pc_positions(state: OverallState, config=None) -> dict:
    """为未设置坐标的 PC 分配到场景出生点附近."""
    scene_id = state.get("scene_id", "")
    scene = state.get("scene")
    actors = state.get("actors", {})
    pcs: dict[str, PlayerCharacter] = state.get("pcs", {})

    if not pcs or not scene_id:
        return {"pcs": pcs}

    pc_list = list(pcs.values())
    pc_positions = _assign_pc_positions(pc_list, scene, actors, spawn_radius=2)

    for pc_id, pos in pc_positions.items():
        if pc_id in pcs:
            pcs[pc_id].position_x = pos["x"]
            pcs[pc_id].position_y = pos["y"]

    for pc in pcs.values():
        pc.scene_id = scene_id

    return {"pcs": pcs}


def _assign_pc_positions(
    pcs: list[PlayerCharacter],
    scene: Scene | None,
    actors: dict[str, Actor] | None = None,
    spawn_radius: int = 2,
) -> dict[str, dict[str, int]]:
    """把未设置坐标的 PC 分配到场景出生点附近，返回 id→{x,y} 映射."""
    scene_id = scene.id if scene else ""
    unset_pcs = [
        pc
        for pc in pcs
        if (pc.position_x == 0 and pc.position_y == 0) or getattr(pc, "scene_id", "") != scene_id
    ]
    if not unset_pcs:
        return {}

    spawn_x = scene.spawn_x if scene else 0
    spawn_y = scene.spawn_y if scene else 0

    occupied = build_occupied(
        {pc.id: pc for pc in pcs if pc not in unset_pcs},
        actors,
    )
    occupied |= load_blocked_tiles(scene)

    positions: dict[str, dict[str, int]] = {}
    offsets = [
        (dx, dy)
        for radius in range(spawn_radius + 1)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if max(abs(dx), abs(dy)) == radius
    ]

    for pc in unset_pcs:
        x, y = spawn_x, spawn_y
        for dx, dy in offsets:
            candidate = (spawn_x + dx, spawn_y + dy)
            if candidate not in occupied:
                x, y = candidate
                break
        else:
            x, y = find_vacant(spawn_x, spawn_y, occupied)

        pc.position_x = x
        pc.position_y = y
        positions[pc.id] = {"x": x, "y": y}
        occupied.add((x, y))

    return positions

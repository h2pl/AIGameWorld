"""Explore Engine——处理角色探索动作 / Handle character explore actions.

生成随机路径点（waypoints），PC 从当前位置依次行进到各个点，
最终坐标写入 DB。路径坐标组合返回给前端，由前端决定行进动画。
地图边界从 scene_info 中读取（来自 world-pack YAML 的 grid 配置）。
"""

import random

from langchain_core.runnables.config import RunnableConfig

from ...utils.helpers import get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

# 路径点数量 / Number of waypoints
WAYPOINT_COUNT = 3
# 地图边距（避开地图边缘）/ Map margin to avoid edges
MAP_MARGIN = 1


async def process_explore_action(
    decision: dict,
    scene_info: dict,
    config: RunnableConfig = None,
) -> dict | None:
    """处理单个 explore 决策 → 生成随机路径点，最终坐标入库 /
    Resolve a single explore decision — generate random waypoints, persist final pos."""
    if decision.get("type") != "explore":
        return None

    pc_id = decision.get("pc_id", "")

    # 获取地图边界和 PC 当前位置 / Get map bounds and PC's current position
    map_width, map_height = _get_map_bounds(scene_info)
    start_x, start_y = _get_pc_position(pc_id, scene_info)

    # 在地图范围内生成随机路径点 / Generate random waypoints within map bounds
    waypoints = _generate_waypoints(map_width, map_height, WAYPOINT_COUNT)
    final_pos = waypoints[-1] if waypoints else {"x": start_x, "y": start_y}

    # 最终坐标入库 / Persist final position to DB
    await _save_pc_position(pc_id, final_pos["x"], final_pos["y"], config)

    logger.info(
        "[engine] %s explore: (%d,%d) → %d waypoints → final (%d,%d) map=%dx%d",
        pc_id,
        start_x,
        start_y,
        len(waypoints),
        final_pos["x"],
        final_pos["y"],
        map_width,
        map_height,
    )

    return {
        "kind": "pc_explore",
        "pc_id": pc_id,
        "start_x": start_x,
        "start_y": start_y,
        "waypoints": waypoints,
        "final_x": final_pos["x"],
        "final_y": final_pos["y"],
    }


def _get_map_bounds(scene_info: dict) -> tuple[int, int]:
    """从 scene_info 获取地图宽高 / Get map width/height from scene_info."""
    scene = scene_info.get("scene", {})
    w = scene.get("map_width", 40)
    h = scene.get("map_height", 40)
    return int(w), int(h)


def _get_pc_position(pc_id: str, scene_info: dict) -> tuple[int, int]:
    """从 scene_info 中获取 PC 当前坐标 / Get PC's current position from scene_info."""
    pcs = scene_info.get("pcs", [])
    for pc in pcs:
        if pc.get("id") == pc_id:
            return pc.get("position_x", 0), pc.get("position_y", 0)
    # 回退到 pc_positions / fallback to pc_positions
    positions = scene_info.get("pc_positions", {})
    pos = positions.get(pc_id, {"x": 0, "y": 0})
    return pos.get("x", 0), pos.get("y", 0)


def _generate_waypoints(map_width: int, map_height: int, count: int) -> list[dict]:
    """在整个地图范围内（留边距）生成随机路径点 /
    Generate random waypoints within the entire map bounds (with margin)."""
    x_min = MAP_MARGIN
    y_min = MAP_MARGIN
    x_max = max(x_min, map_width - MAP_MARGIN - 1)
    y_max = max(y_min, map_height - MAP_MARGIN - 1)
    waypoints: list[dict] = []
    for _ in range(count):
        x = random.randint(x_min, x_max)
        y = random.randint(y_min, y_max)
        waypoints.append({"x": x, "y": y})
    return waypoints


async def _save_pc_position(
    pc_id: str,
    x: int,
    y: int,
    config: RunnableConfig = None,
) -> None:
    """把 PC 最终坐标写入 DB / Save PC's final position to DB."""
    pc_repo = get_repo(config, "char")
    if not pc_repo:
        return
    pc = await pc_repo.load_pc(pc_id)
    if pc:
        pc.position_x = x
        pc.position_y = y
        await pc_repo.save_pc(pc)

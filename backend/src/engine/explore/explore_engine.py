"""Explore Engine——处理角色探索动作 / Handle character explore actions.

从 PC 当前位置出发，生成随机多段连续路径（A→B→C→D），
每段步长有限，保证行走连续性。最终坐标更新到 pc_state_map。
"""

import random

from ...utils.logging import get_logger

logger = get_logger(__name__)

# 路径段数范围 / Waypoint segment count range
SEGMENT_MIN = 2
SEGMENT_MAX = 5
# 每段步长范围（tile）/ Per-segment step range
STEP_MIN = 3
STEP_MAX = 8
# 地图边距 / Map margin
MAP_MARGIN = 1


def process_explore_action(
    decision: dict,
    scene_info: dict,
    pc_state_map: dict[str, dict],
    actor_state_map: dict[str, dict] | None = None,
) -> dict | None:
    """处理单个 explore 决策 → 生成多段连续路径，更新 pc_state_map."""
    if decision.get("type") != "explore":
        return None

    pc_id = decision.get("pc_id", "")
    map_width, map_height = _get_map_bounds(scene_info)
    start_x, start_y = _get_pc_position(pc_id, pc_state_map)

    occupied = _build_occupied_set(pc_state_map, actor_state_map, exclude_id=pc_id)

    # 从起点出发，生成多段连续路径 / Multi-segment path from start
    waypoints = _generate_path(start_x, start_y, map_width, map_height, occupied)
    final_pos = waypoints[-1] if waypoints else {"x": start_x, "y": start_y}

    # 更新 PC 运行时状态
    if pc_id in pc_state_map:
        pc_state_map[pc_id]["position_x"] = final_pos["x"]
        pc_state_map[pc_id]["position_y"] = final_pos["y"]

    logger.info(
        "[engine] %s explore: (%d,%d) → %d steps → final (%d,%d) map=%dx%d",
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
    scene = scene_info.get("scene", {})
    return int(scene.get("map_width", 40)), int(scene.get("map_height", 40))


def _get_pc_position(pc_id: str, pc_state_map: dict[str, dict]) -> tuple[int, int]:
    info = pc_state_map.get(pc_id, {})
    return info.get("position_x", 0), info.get("position_y", 0)


def _generate_path(
    start_x: int,
    start_y: int,
    map_width: int,
    map_height: int,
    occupied: set[tuple[int, int]] | None = None,
) -> list[dict]:
    """从起点出发，生成随机多段连续路径，避免角色重叠"""
    occupied = occupied or set()
    segment_count = random.randint(SEGMENT_MIN, SEGMENT_MAX)
    x_bounds = (MAP_MARGIN, max(MAP_MARGIN, map_width - MAP_MARGIN - 1))
    y_bounds = (MAP_MARGIN, max(MAP_MARGIN, map_height - MAP_MARGIN - 1))

    waypoints: list[dict] = []
    cur_x, cur_y = start_x, start_y

    for _ in range(segment_count):
        for _retry in range(8):  # 最多重试 8 次找空位 / Retry up to 8 times
            step_x = random.randint(STEP_MIN, STEP_MAX) * random.choice((-1, 1))
            step_y = random.randint(STEP_MIN, STEP_MAX) * random.choice((-1, 1))
            next_x = _clamp(cur_x + step_x, x_bounds[0], x_bounds[1])
            next_y = _clamp(cur_y + step_y, y_bounds[0], y_bounds[1])
            if next_x == cur_x and next_y == cur_y:
                continue  # 原地踏步，重试 / No movement, retry
            if (next_x, next_y) not in occupied:
                break
        else:
            next_x, next_y = cur_x, cur_y  # 8 次都没空位则不动
        cur_x, cur_y = next_x, next_y
        waypoints.append({"x": cur_x, "y": cur_y})

    return waypoints


def _build_occupied_set(
    pc_state_map: dict[str, dict] | None,
    actor_state_map: dict[str, dict] | None,
    exclude_id: str = "",
) -> set[tuple[int, int]]:
    """收集所有角色占用的坐标（排除 exclude_id）"""
    occupied: set[tuple[int, int]] = set()
    for src in (pc_state_map, actor_state_map):
        if not src:
            continue
        for cid, info in src.items():
            if cid == exclude_id:
                continue
            x = info.get("position_x", 0)
            y = info.get("position_y", 0)
            if x or y:
                occupied.add((x, y))
    return occupied


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))

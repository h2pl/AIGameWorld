"""Explore Engine——LLM 驱动的角色探索 / LLM-driven character explore actions.

从 PC 当前位置出发，LLM 决定 1-3 个探索路径点，每点生成一段第三人称旁白。
最终坐标更新到 pc_state_map。
"""

import random
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.llm_output import ExploreOutputSchema, ExploreWaypointSchema
from ...services.memory_service import retrieve_memories
from ...utils.helpers import get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))

# 随机路径参数 / Random path fallback params
SEGMENT_MIN = 2
SEGMENT_MAX = 4
STEP_MIN = 3
STEP_MAX = 8
MAP_MARGIN = 1


async def process_explore_action(
    decision: dict,
    scene_info: dict,
    pc_state_map: dict[str, dict],
    actor_state_map: dict[str, dict] | None = None,
    tick: int = 0,
    config: RunnableConfig = None,
) -> dict | None:
    """处理单个 explore 决策 → LLM 生成路径+旁白，更新 pc_state_map."""
    if decision.get("type") != "explore":
        return None

    pc_id = decision.get("pc_id", "")
    map_width, map_height = _get_map_bounds(scene_info)
    start_x, start_y = _get_pc_position(pc_id, pc_state_map)

    waypoints = await _generate_waypoints(
        pc_id=pc_id,
        scene_info=scene_info,
        start_x=start_x,
        start_y=start_y,
        map_width=map_width,
        map_height=map_height,
        config=config,
    )

    if not waypoints:
        # 降级：LLM 不可用时用随机路径 + 简单旁白
        waypoints = _fallback_waypoints(
            start_x, start_y, map_width, map_height, pc_state_map, actor_state_map, pc_id
        )

    # 更新 PC 运行时状态到最终路径点
    final = waypoints[-1]
    if pc_id in pc_state_map:
        pc_state_map[pc_id]["position_x"] = final["x"]
        pc_state_map[pc_id]["position_y"] = final["y"]

    # 存储探索记忆 / Store exploration memory
    await _store_explore_memory(pc_id, waypoints, tick, config)

    logger.info(
        "[engine] %s explore: (%d,%d) → %d waypoints → final (%d,%d)",
        pc_id,
        start_x,
        start_y,
        len(waypoints),
        final["x"],
        final["y"],
    )

    return {
        "kind": "pc_explore",
        "pc_id": pc_id,
        "start_x": start_x,
        "start_y": start_y,
        "waypoints": waypoints,
        "final_x": final["x"],
        "final_y": final["y"],
    }


async def _generate_waypoints(
    pc_id: str,
    scene_info: dict,
    start_x: int,
    start_y: int,
    map_width: int,
    map_height: int,
    config: RunnableConfig = None,
) -> list[dict]:
    """调用 LLM 生成探索路径点 + 旁白."""
    llm = get_llm(config)
    if llm is None:
        return []

    pc = _find_pc(pc_id, scene_info)
    scene = scene_info.get("scene", {})
    plot_brief = scene_info.get("plot_brief", "")
    hints = scene_info.get("hints", [])

    query = f"{plot_brief} {scene.get('description', '')}".strip()
    memories = await retrieve_memories(pc_id, query, config=config, top_k=5)

    ctx = {
        "pc": pc,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memories,
        "scene": scene,
        "map_width": map_width,
        "map_height": map_height,
        "landmarks": scene.get("landmarks", []),
        "scene_objects": scene_info.get("scene_objects", []),
        "start_x": start_x,
        "start_y": start_y,
    }

    try:
        system = _PROMPTS.get_template("explore/_explore_system.jinja").render(**ctx)
        prompt = _PROMPTS.get_template("explore/explore_path.jinja").render(**ctx)
    except Exception:
        logger.exception("[engine] explore prompt render failed")
        return []

    try:
        result = await llm.call_structured(
            "explore",
            ExploreOutputSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: ExploreOutputSchema(waypoints=[]),
        )
    except Exception:
        logger.exception("[engine] explore generation failed for %s", pc_id)
        return []

    return _clamp_and_validate(result.waypoints, map_width, map_height, start_x, start_y)


def _clamp_and_validate(
    waypoints: list[ExploreWaypointSchema],
    map_width: int,
    map_height: int,
    start_x: int,
    start_y: int,
) -> list[dict]:
    """校验并裁剪 LLM 坐标到地图范围内，至少保留起点."""
    valid: list[dict] = []
    prev_x, prev_y = start_x, start_y
    for wp in waypoints:
        x = max(0, min(map_width - 1, wp.x))
        y = max(0, min(map_height - 1, wp.y))
        # 跳过原地踏步 / Skip no-op
        if x == prev_x and y == prev_y:
            continue
        valid.append({"x": x, "y": y, "narration": wp.narration or "此处一片寂静。"})
        prev_x, prev_y = x, y
    return valid


def _fallback_waypoints(
    start_x: int,
    start_y: int,
    map_width: int,
    map_height: int,
    pc_state_map: dict[str, dict] | None,
    actor_state_map: dict[str, dict] | None,
    pc_id: str,
) -> list[dict]:
    """LLM 不可用时生成随机路径 + 简单旁白."""
    from ...utils.helpers import build_occupied_set

    occupied = build_occupied_set(pc_state_map, actor_state_map, exclude_id=pc_id)
    segment_count = random.randint(SEGMENT_MIN, SEGMENT_MAX)
    x_bounds = (MAP_MARGIN, max(MAP_MARGIN, map_width - MAP_MARGIN - 1))
    y_bounds = (MAP_MARGIN, max(MAP_MARGIN, map_height - MAP_MARGIN - 1))

    waypoints: list[dict] = []
    cur_x, cur_y = start_x, start_y
    for _ in range(segment_count):
        for _retry in range(8):
            step_x = random.randint(STEP_MIN, STEP_MAX) * random.choice((-1, 1))
            step_y = random.randint(STEP_MIN, STEP_MAX) * random.choice((-1, 1))
            next_x = max(x_bounds[0], min(x_bounds[1], cur_x + step_x))
            next_y = max(y_bounds[0], min(y_bounds[1], cur_y + step_y))
            if next_x == cur_x and next_y == cur_y:
                continue
            if (next_x, next_y) not in occupied:
                break
        else:
            next_x, next_y = cur_x, cur_y
        cur_x, cur_y = next_x, next_y
        waypoints.append(
            {"x": cur_x, "y": cur_y, "narration": f"探索到了 ({cur_x}, {cur_y}) 附近。"}
        )
    return waypoints


def _find_pc(pc_id: str, scene_info: dict) -> dict:
    """在 scene_info 中查找 PC 信息."""
    for pc in scene_info.get("pcs", []):
        if pc.get("id") == pc_id:
            return pc
    return {"id": pc_id, "name": pc_id}


def _get_map_bounds(scene_info: dict) -> tuple[int, int]:
    scene = scene_info.get("scene", {})
    return int(scene.get("map_width", 40)), int(scene.get("map_height", 40))


def _get_pc_position(pc_id: str, pc_state_map: dict[str, dict]) -> tuple[int, int]:
    info = pc_state_map.get(pc_id, {})
    return info.get("position_x", 0), info.get("position_y", 0)


async def _store_explore_memory(
    pc_id: str,
    waypoints: list[dict],
    tick: int,
    config: RunnableConfig = None,
) -> None:
    """把探索到的内容存入 PC 记忆 / Store exploration findings into PC memory."""
    memory_repo = get_repo(config, "memory")
    if not memory_repo or not waypoints:
        return
    narrations = [wp.get("narration", "") for wp in waypoints if wp.get("narration")]
    if not narrations:
        return
    content = "探索发现：" + "；".join(narrations)
    await memory_repo.store(pc_id, content, tick, importance=2)

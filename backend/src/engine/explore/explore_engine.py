"""Explore Engine——LLM 驱动的角色探索 / LLM-driven character explore actions.

一次只处理一个 explore 决策 → LLM 决定终点坐标 + 探索记录，更新 pc_state_map。
与 talk/interact 一致：一次行动，一条路径，一条探索记录。
目标坐标会避开其他角色（build_occupied_set + find_vacant_adjacent）。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...schemas.engine_result import ExploreActionResult
from ...schemas.llm_output import ExploreOutputSchema
from ...services.memory_service import retrieve_memories
from ...utils.helpers import build_occupied_set, find_vacant_adjacent, get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))


async def process_explore_action(
    decision: dict,
    scene_info: dict,
    pc_state_map: dict[str, dict],
    actor_state_map: dict[str, dict] | None = None,
    plot_brief: str = "",
    hints: list[str] | None = None,
    tick: int = 0,
    config: RunnableConfig = None,
) -> ExploreActionResult | None:
    """处理单个 explore 决策 → LLM 生成终点+探索记录，更新 pc_state_map，防重叠."""
    if decision.get("type") != "explore":
        return None

    pc_id = decision.get("pc_id", "")
    map_width, map_height = _get_map_bounds(scene_info)
    start_x, start_y = _get_pc_position(pc_id, pc_state_map)

    result = await _generate_explore_data(
        pc_id=pc_id,
        scene_info=scene_info,
        plot_brief=plot_brief,
        hints=hints or [],
        start_x=start_x,
        start_y=start_y,
        map_width=map_width,
        map_height=map_height,
        pc_state_map=pc_state_map,
        config=config,
    )

    if not result:
        return None

    end_x = result.end_x
    end_y = result.end_y
    explore_record = result.explore_record

    # 防止角色重叠：检查目的地方格是否被占用，找最近空位
    occupied = build_occupied_set(pc_state_map, actor_state_map, exclude_id=pc_id)
    if (end_x, end_y) in occupied:
        adj_x, adj_y = find_vacant_adjacent(end_x, end_y, occupied)
        logger.info(
            "[engine] %s explore: dest (%d,%d) occupied, adjusted to (%d,%d)",
            pc_id,
            end_x,
            end_y,
            adj_x,
            adj_y,
        )
        end_x, end_y = adj_x, adj_y

    # 更新 PC 坐标
    if pc_id in pc_state_map:
        pc_state_map[pc_id]["position_x"] = end_x
        pc_state_map[pc_id]["position_y"] = end_y

    await _store_explore_memory(pc_id, explore_record, tick, config)

    logger.info(
        "[engine] %s explore: (%d,%d) → (%d,%d) | %s",
        pc_id,
        start_x,
        start_y,
        end_x,
        end_y,
        explore_record[:30],
    )

    return ExploreActionResult(
        pc_id=pc_id,  # 探索者 id
        waypoints=[{"x": start_x, "y": start_y}, {"x": end_x, "y": end_y}],  # 起点→终点
        explore_record=explore_record,  # LLM 生成的探索记录
    )


async def _generate_explore_data(
    pc_id: str,
    scene_info: dict,
    plot_brief: str,
    hints: list[str],
    start_x: int,
    start_y: int,
    map_width: int,
    map_height: int,
    pc_state_map: dict[str, dict],
    config: RunnableConfig = None,
) -> ExploreOutputSchema | None:
    """LLM 生成探索终点坐标 + 探索记录 / LLM generates destination + explore_record."""
    llm = get_llm(config)
    scene = scene_info.get("scene", {})
    pc = _pc_identity(pc_id, pc_state_map)

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

    system = _PROMPTS.get_template("explore/_explore_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("explore/explore.jinja").render(**ctx)

    result = await llm.call_structured(
        "explore",
        ExploreOutputSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )

    result.end_x = max(0, min(map_width - 1, result.end_x))
    result.end_y = max(0, min(map_height - 1, result.end_y))

    if result.end_x == start_x and result.end_y == start_y:
        logger.info("[engine] %s explore: LLM returned same position, skipping", pc_id)
        return None

    return result


def _get_map_bounds(scene_info: dict) -> tuple[int, int]:
    scene = scene_info.get("scene", {})
    return int(scene.get("map_width", 40)), int(scene.get("map_height", 40))


def _get_pc_position(pc_id: str, pc_state_map: dict[str, dict]) -> tuple[int, int]:
    info = pc_state_map.get(pc_id, {})
    return info.get("position_x", 0), info.get("position_y", 0)


async def _store_explore_memory(
    pc_id: str,
    explore_record: str,
    tick: int,
    config: RunnableConfig = None,
) -> None:
    memory_repo = get_repo(config, "memory")
    if not memory_repo or not explore_record:
        return
    content = f"探索发现：{explore_record}"
    await memory_repo.store(pc_id, content, tick, importance=2)


def _pc_identity(pc_id: str, pc_state_map: dict[str, dict]) -> dict:
    info = pc_state_map.get(pc_id, {})
    return {
        "id": pc_id,
        "name": info.get("name", pc_id),
        "role": info.get("role", ""),
        "personality": info.get("personality", ""),
    }

"""Explore Engine——LLM 驱动的角色探索 / LLM-driven character explore actions.

一次只处理一个 explore 决策 → LLM 决定终点坐标 + 探索记录，直接修改 pcs 中的 PC 领域模型。
与 talk/interact 一致：一次行动，一条路径，一条探索记录。
目标坐标会避开其他角色（build_occupied_set + find_vacant_adjacent）。
"""

from pathlib import Path
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from src.utils.tracing import traced

from ...domain import (
    Action,
    Actor,
    Decision,
    DMRecord,
    Memory,
    MemoryType,
    PlayerCharacter,
    Scene,
    SceneObject,
    importance_of,
)
from ...schemas.llm_output import ExploreOutputSchema
from ...services.memory_service import retrieve_memories
from ...utils.helpers import dict_without, get_llm, validate_position
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))


@traced()
async def process_explore_action(
    decision: Decision,
    tick: int,
    scene: Scene | None = None,
    scene_objects: list[SceneObject] | None = None,
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
    dm_record: DMRecord | None = None,
    memories: dict[str, list[Memory]] | None = None,
    config: RunnableConfig = None,
) -> Action | None:
    """处理单个 explore 决策 → LLM 生成终点+探索记录，直接修改 PC 领域模型，防重叠."""
    if decision.type != "explore":
        return None

    pc_id = decision.pc_id
    pc = (pcs or {}).get(pc_id)
    if pc is None:
        return None

    # 从 dm_record 读取剧情上下文 / Read plot context from dm_record
    plot_brief = dm_record.plot_brief if dm_record else ""
    hints = dm_record.hints if dm_record else []

    # 获取地图边界 / Get map bounds
    map_width, map_height = _get_map_bounds(scene)
    # 记录起点 / Record start position（应与 scene_setup 事件中该 PC 的坐标一致）
    start_x, start_y = pc.position_x, pc.position_y
    logger.info(
        "[engine] %s explore start pos=(%d,%d) scene=%s",
        pc_id,
        start_x,
        start_y,
        scene.id if scene else "?",
    )

    # 调用 LLM 生成探索目的地与记录 / Generate destination and record via LLM
    result = await _generate_explore_data(
        pc_id=pc_id,
        scene=scene,
        scene_objects=scene_objects,
        plot_brief=plot_brief,
        hints=hints,
        start_x=start_x,
        start_y=start_y,
        map_width=map_width,
        map_height=map_height,
        pcs=pcs,
        tick=tick,
        memories=memories,
        config=config,
    )

    if not result:
        return None

    end_x = result.end_x
    end_y = result.end_y
    explore_record = result.explore_record

    # 防止角色重叠 + 地图碰撞 / Avoid overlap and map collision
    old_x, old_y = end_x, end_y
    end_x, end_y = validate_position(
        end_x, end_y, dict_without(pcs, pc_id), actors, scene, scene_objects
    )
    # 如果坐标被调整则记录日志 / Log if destination was adjusted
    if (old_x, old_y) != (end_x, end_y):
        logger.info(
            "[engine] %s explore: dest (%d,%d) blocked, adjusted to (%d,%d)",
            pc_id,
            old_x,
            old_y,
            end_x,
            end_y,
        )

    # 直接修改 PC 领域模型坐标 / Mutate PC domain model coordinates
    pc.position_x = end_x
    pc.position_y = end_y

    # 写入本 tick 记忆 / Stage memory for current tick
    _store_explore_memory(pc_id, explore_record, tick, memories)

    logger.info(
        "[engine] %s explore: (%d,%d) → (%d,%d) | %s",
        pc_id,
        start_x,
        start_y,
        end_x,
        end_y,
        explore_record[:30],
    )

    return Action(
        pc_id=pc_id,
        action_type="explore",
        target_id="",
        target_type="",
        waypoints=[{"x": start_x, "y": start_y}, {"x": end_x, "y": end_y}],
        explore_record=explore_record,
    )


async def _generate_explore_data(
    pc_id: str,
    scene: Scene | None,
    scene_objects: list[SceneObject] | None,
    plot_brief: str,
    hints: list[str],
    start_x: int,
    start_y: int,
    map_width: int,
    map_height: int,
    pcs: dict[str, PlayerCharacter] | None,
    tick: int,
    memories: dict[str, list[Memory]] | None,
    config: RunnableConfig = None,
) -> ExploreOutputSchema | None:
    """LLM 生成探索终点坐标 + 探索记录 / LLM generates destination + explore_record."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[explore] LLM client not configured")

    pc = _pc_identity(pc_id, pcs)

    query = f"{scene.name if scene else ''} 探索周围环境".strip()
    # 反思检索用叙事性情境描述 / Narrative query for reflection retrieval
    reflection_query = f"{pc['name']}在{scene.name if scene else '未知场景'}，观察周围的环境"
    if plot_brief:
        reflection_query += f"，{plot_brief}"
    memory_texts = await retrieve_memories(
        pc_id,
        query,
        config=config,
        top_k=5,
        current_tick=tick,
        reflection_query=reflection_query,
    )

    ctx = {
        "pc": pc,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memory_texts,
        "scene": scene or {},
        "map_width": map_width,
        "map_height": map_height,
        "scene_objects": scene_objects or [],
        "start_x": start_x,
        "start_y": start_y,
    }

    system = _PROMPTS.get_template("explore/_explore_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("explore/explore.jinja").render(**ctx)

    # 调用 LLM 生成探索结果 / Call LLM to generate exploration result
    result = await llm.call_structured(
        "explore",
        ExploreOutputSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )

    # 将坐标限制在地图范围内 / Clamp coordinates within map bounds
    result.end_x = max(0, min(map_width - 1, result.end_x))
    result.end_y = max(0, min(map_height - 1, result.end_y))

    # 如果 LLM 返回原地则跳过 / Skip if LLM returns same position
    if result.end_x == start_x and result.end_y == start_y:
        logger.info("[engine] %s explore: LLM returned same position, skipping", pc_id)
        return None

    return result


def _get_map_bounds(scene: Scene | None) -> tuple[int, int]:
    if scene is None:
        return 40, 40
    return scene.map_width, scene.map_height


def _store_explore_memory(
    pc_id: str,
    explore_record: str,
    tick: int,
    memories: dict[str, list[Memory]] | None,
) -> None:
    if memories is None or not explore_record:
        return
    memories.setdefault(pc_id, []).append(
        Memory(
            id=f"mem_{pc_id}_{tick}_{uuid4().hex[:6]}",
            pc_id=pc_id,
            content=f"探索发现：{explore_record}",
            tick=tick,
            importance=importance_of(MemoryType.EXPLORE.value),
            memory_type=MemoryType.EXPLORE.value,
            entity_type="pc",
        )
    )


def _pc_identity(pc_id: str, pcs: dict[str, PlayerCharacter] | None) -> dict:
    pc = (pcs or {}).get(pc_id)
    if pc is None:
        return {"id": pc_id, "name": pc_id, "role": "", "personality": ""}
    return {
        "id": pc_id,
        "name": pc.name,
        "role": pc.role,
        "personality": pc.personality,
    }

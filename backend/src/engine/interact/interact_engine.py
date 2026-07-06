"""Interact Engine——场景对象交互 / Scene object interaction.

一次性 LLM 调用：根据 PC、物体、场景上下文，直接生成交互结果（success + narration）。
不掷骰、不检定，由 LLM 基于角色能力和物体特性合理判断。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...domain.scene_object import SceneObject
from ...schemas.engine_result import InteractActionResult
from ...schemas.llm_output import InteractOutputSchema
from ...services.memory_service import retrieve_memories
from ...utils.helpers import build_occupied_set, find_vacant_adjacent, get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))


async def process_interact_action(
    decision: dict,
    scene_info: dict | None = None,
    pc_state_map: dict[str, dict] | None = None,
    actor_state_map: dict[str, dict] | None = None,
    tick: int = 0,
    plot_brief: str = "",
    hints: list[str] | None = None,
    config: RunnableConfig = None,
) -> InteractActionResult | None:
    """处理单个 interact 决策：移动→LLM 裁决→记忆 / Resolve interact: move → LLM judge → memory."""
    if decision.get("type") != "interact":
        return None
    object_id = decision.get("target_id", "")
    if not object_id:
        return None

    char_id = decision.get("pc_id", "")
    scene_obj = await _load_scene_object(get_repo(config, "scene"), object_id)

    # 移动到物体旁边并记录路径 / Move PC adjacent to object and record waypoints
    waypoints = _move_to_object(char_id, object_id, scene_info, pc_state_map, actor_state_map)

    # LLM 生成交互结果 / Generate interaction result via LLM
    interact_result = await _generate_interact(
        pc_id=char_id,
        object_id=object_id,
        scene_info=scene_info,
        pc_state_map=pc_state_map or {},
        plot_brief=plot_brief,
        hints=hints or [],
        config=config,
    )

    success = interact_result.get("success", False)
    narration = interact_result.get("narration", "")

    # 存入记忆 / Store memory
    await _store_interact_memory(char_id, object_id, scene_obj, success, narration, tick, config)

    logger.info(
        "[interact] %s → %s : %s | %s",
        char_id,
        object_id,
        "success" if success else "fail",
        narration[:30],
    )
    return InteractActionResult(
        pc_id=char_id,
        object_id=object_id,
        success=success,
        waypoints=waypoints,
        narration=narration,
    )


async def _load_scene_object(scene_repo, object_id: str) -> SceneObject | None:
    """按 id 查询场景对象 / Fetch a scene object by id."""
    if not scene_repo or not object_id:
        return None
    all_objects = await scene_repo.load_all()
    return all_objects.get(object_id)


async def _generate_interact(
    pc_id: str,
    object_id: str,
    scene_info: dict | None,
    pc_state_map: dict[str, dict],
    plot_brief: str,
    hints: list[str],
    config: RunnableConfig = None,
) -> dict:
    """LLM 生成交互结果（success + narration）/ LLM generates interact result."""
    llm = get_llm(config)
    pc = _pc_identity(pc_id, pc_state_map)
    obj = _find_scene_object(object_id, scene_info)
    scene = (scene_info or {}).get("scene", {})

    query = f"{plot_brief} {obj.get('name', '')} {scene.get('description', '')}".strip()
    memories = await retrieve_memories(pc_id, query, config=config, top_k=5)

    ctx = {
        "pc": pc,
        "obj": obj,
        "scene": scene,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memories,
    }

    system = _PROMPTS.get_template("interact/_interact_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("interact/interact.jinja").render(**ctx)

    raw = await llm.call_structured(
        "interact",
        InteractOutputSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )
    return {"success": raw.success, "narration": raw.narration}


def _move_to_object(
    pc_id: str,
    object_id: str,
    scene_info: dict | None,
    pc_state_map: dict[str, dict] | None,
    actor_state_map: dict[str, dict] | None = None,
) -> list[dict]:
    """将 PC 移动到目标物体旁边的空位，返回 waypoints / Move PC adjacent to object."""
    if not pc_state_map or pc_id not in pc_state_map:
        return []

    obj = _find_scene_object(object_id, scene_info)
    tx = obj.get("position_x", 0) if obj else 0
    ty = obj.get("position_y", 0) if obj else 0
    if tx == 0 and ty == 0:
        return []

    old_x = pc_state_map[pc_id].get("position_x", 0)
    old_y = pc_state_map[pc_id].get("position_y", 0)

    occupied = build_occupied_set(pc_state_map, actor_state_map, exclude_id=pc_id)
    new_x, new_y = find_vacant_adjacent(tx, ty, occupied)

    pc_state_map[pc_id]["position_x"] = new_x
    pc_state_map[pc_id]["position_y"] = new_y
    if old_x == new_x and old_y == new_y:
        return []
    return [{"x": old_x, "y": old_y}, {"x": new_x, "y": new_y}]


def _find_scene_object(object_id: str, scene_info: dict | None) -> dict:
    """在 scene_info 中查找场景物体 / Find scene object in scene_info."""
    if not scene_info:
        return {}
    for obj in scene_info.get("scene_objects", []):
        if obj.get("id") == object_id:
            return obj
    return {}


def _pc_identity(pc_id: str, pc_state_map: dict[str, dict]) -> dict:
    """从 pc_state_map 读取 PC 身份 / Read PC identity from state map."""
    info = pc_state_map.get(pc_id, {})
    return {
        "id": pc_id,
        "name": info.get("name", pc_id),
        "role": info.get("role", ""),
        "personality": info.get("personality", ""),
    }


async def _store_interact_memory(
    pc_id: str,
    object_id: str,
    scene_obj: SceneObject | None,
    success: bool,
    narration: str,
    tick: int,
    config: RunnableConfig = None,
) -> None:
    """把交互结果存入 PC 记忆 / Store interaction result into PC memory."""
    memory_repo = get_repo(config, "memory")
    if not memory_repo:
        return
    obj_name = scene_obj.name if scene_obj else object_id
    content = f"与 {obj_name} 交互（{'成功' if success else '失败'}）：{narration}"
    await memory_repo.store(pc_id, content, tick, importance=4)

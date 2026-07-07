"""Interact Engine——场景对象交互 / Scene object interaction.

一次性 LLM 调用：根据 PC、物体、场景上下文，直接生成交互结果（success + narration）。
不掷骰、不检定，由 LLM 基于角色能力和物体特性合理判断。
"""

from pathlib import Path
from typing import Any
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...domain import Actor, Memory, PlayerCharacter
from ...domain.scene_object import SceneObject
from ...schemas.engine_result import InteractActionResult
from ...schemas.llm_output import InteractOutputSchema
from ...services.memory_service import retrieve_memories
from ...utils.helpers import dict_without, get_llm, get_repo, validate_position
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))


async def process_interact_action(
    decision: dict,
    scene: dict[str, Any] | None = None,
    scene_objects: list[dict[str, Any]] | None = None,
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
    tick: int = 0,
    plot_brief: str = "",
    hints: list[str] | None = None,
    pc_memory_map: dict[str, list[Memory]] | None = None,
    config: RunnableConfig = None,
) -> InteractActionResult | None:
    """处理单个 interact 决策：移动→LLM 裁决→记忆 / Resolve interact: move → LLM judge → memory."""
    if decision.get("type") != "interact":
        return None
    object_id = decision.get("target_id", "")
    if not object_id:
        return None

    char_id = decision.get("pc_id", "")
    pc = (pcs or {}).get(char_id)
    if pc is None:
        return None
    scene_obj = await _load_scene_object(get_repo(config, "scene"), object_id)

    # 移动到物体旁边并记录路径 / Move PC adjacent to object and record waypoints
    waypoints = _move_to_object(char_id, object_id, scene, scene_objects, pcs, actors)

    # LLM 生成交互结果 / Generate interaction result via LLM
    interact_result = await _generate_interact(
        pc_id=char_id,
        object_id=object_id,
        scene=scene or {},
        scene_objects=scene_objects or [],
        pc=pc,
        plot_brief=plot_brief,
        hints=hints or [],
        tick=tick,
        pc_memory_map=pc_memory_map,
        config=config,
    )

    success = interact_result.get("success", False)
    narration = interact_result.get("narration", "")

    # 存入记忆 / Stage memory
    _store_interact_memory(char_id, object_id, scene_obj, success, narration, tick, pc_memory_map)

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
    scene: dict[str, Any],
    scene_objects: list[dict[str, Any]],
    pc: PlayerCharacter,
    plot_brief: str,
    hints: list[str],
    tick: int,
    pc_memory_map: dict[str, list[dict]] | None,
    config: RunnableConfig = None,
) -> dict:
    """LLM 生成交互结果（success + narration）/ LLM generates interact result."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[interact] LLM client not configured")
    obj = _find_scene_object(object_id, scene, scene_objects)

    query = f"{plot_brief} {obj.name if obj else ''} {scene.description}".strip()
    memories = await retrieve_memories(
        pc_id, query, config=config, top_k=5, pc_memory_map=pc_memory_map, current_tick=tick
    )

    ctx = {
        "pc": _pc_identity(pc),
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
    scene: Scene,
    scene_objects: list[SceneObject],
    pcs: dict[str, PlayerCharacter] | None,
    actors: dict[str, Actor] | None = None,
) -> list[dict]:
    """将 PC 移动到目标物体旁边的空位，返回 waypoints / Move PC adjacent to object."""
    if not pcs or pc_id not in pcs:
        return []
    pc = pcs[pc_id]

    obj = _find_scene_object(object_id, scene, scene_objects)
    tx = obj.position_x if obj else 0
    ty = obj.position_y if obj else 0
    if tx == 0 and ty == 0:
        return []

    old_x, old_y = pc.position_x, pc.position_y

    new_x, new_y = validate_position(tx, ty, dict_without(pcs, pc_id), actors, scene, scene_objects)

    pc.position_x = new_x
    pc.position_y = new_y
    if old_x == new_x and old_y == new_y:
        return []
    return [{"x": old_x, "y": old_y}, {"x": new_x, "y": new_y}]


def _find_scene_object(
    object_id: str,
    scene: Scene,
    scene_objects: list[SceneObject],
) -> SceneObject | None:
    """在 scene_objects 中按 id 查找场景物体."""
    for obj in scene_objects:
        if obj.id == object_id:
            return obj
    return None


def _pc_identity(pc: PlayerCharacter) -> dict:
    """读取 PC 身份 / Read PC identity."""
    return {
        "id": pc.id,
        "name": pc.name,
        "role": pc.role,
        "personality": pc.personality,
    }


def _store_interact_memory(
    pc_id: str,
    object_id: str,
    scene_obj: SceneObject | None,
    success: bool,
    narration: str,
    tick: int,
    pc_memory_map: dict[str, list[Memory]] | None,
) -> None:
    """把交互结果写入 pc_memory_map / Stage interaction result into state."""
    if pc_memory_map is None:
        return
    obj_name = scene_obj.name if scene_obj else object_id
    content = f"与 {obj_name} 交互（{'成功' if success else '失败'}）：{narration}"
    pc_memory_map.setdefault(pc_id, []).append(
        Memory(
            id=f"mem_{pc_id}_{tick}_{uuid4().hex[:6]}",
            pc_id=pc_id,
            content=content,
            tick=tick,
            importance=4,
            memory_type="interact",
            entity_type="pc",
        )
    )

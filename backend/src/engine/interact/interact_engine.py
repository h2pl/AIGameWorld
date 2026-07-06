"""Interact Engine——场景对象交互裁决 + 旁白 / Scene object interaction resolution + narration."""

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...domain.scene_object import SceneObject, SceneObjectType
from ...rules.dnd_rules import ability_modifier, resolve_check
from ...schemas.llm_output import InteractNarrationSchema
from ...schemas.request import SceneObjectInteractRequest
from ...schemas.response import SceneObjectInteractResponse
from ...services.memory_service import retrieve_memories
from ...utils.helpers import build_occupied_set, find_vacant_adjacent, get_llm, get_repo
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))

# object_type/interact_data → (action_type, 检定属性, 默认 dc) / → (action_type, check ability, default dc)
_TRAP_DC = 12
_DOOR_DC = 13
_LOCK_DC = 12

_ACTION_CN = {
    "pick_lock": "开锁",
    "disarm_trap": "拆陷阱",
    "break_door": "破门",
    "open_chest": "开宝箱",
    "interact": "交互",
}


def resolve_interact(req: SceneObjectInteractRequest) -> SceneObjectInteractResponse:
    """对象交互检定 / Object interaction check.

    dc <= 0 表示无需检定（如未上锁的容器/门），直接判定成功，不掷骰 /
    dc <= 0 means no check is required (e.g. an unlocked container/door);
    it's an automatic success without rolling.
    """
    action_cn = _ACTION_CN.get(req.action_type, req.action_type or "交互")
    if req.dc <= 0:
        return SceneObjectInteractResponse(
            success=True,
            result={
                "object_id": req.object_id,
                "pc_id": req.pc_id,
                "action": req.action_type,
                "action_cn": action_cn,
                "roll": None,
                "bonus": req.attribute_mod,
                "dc": req.dc,
                "total": None,
                "critical": False,
                "fumble": False,
            },
        )
    result = resolve_check(bonus=req.attribute_mod, dc=req.dc)
    return SceneObjectInteractResponse(
        success=result.success,
        result={
            "object_id": req.object_id,
            "pc_id": req.pc_id,
            "action": req.action_type,
            "action_cn": action_cn,
            "roll": result.roll,
            "bonus": req.attribute_mod,
            "dc": req.dc,
            "total": result.total,
            "critical": result.is_critical,
            "fumble": result.is_fumble,
        },
    )


async def process_interact_action(
    decision: dict,
    scene_info: dict | None = None,
    pc_state_map: dict[str, dict] | None = None,
    actor_state_map: dict[str, dict] | None = None,
    tick: int = 0,
    plot_brief: str = "",
    hints: list[str] | None = None,
    config: RunnableConfig = None,
) -> dict | None:
    """处理单个 interact 决策：移动→检定→旁白→记忆 / Resolve interact: move → check → narrate → memory."""
    if decision.get("type") != "interact":
        return None
    object_id = decision.get("target_id", "")
    if not object_id:
        return None

    char_id = decision.get("pc_id", "")
    scene_obj = await _load_scene_object(get_repo(config, "scene"), object_id)
    action_type, ability, dc = _interact_requirements(scene_obj)
    attribute_mod = await _ability_mod_for(get_repo(config, "char"), char_id, ability)

    result = resolve_interact(
        SceneObjectInteractRequest(
            object_id=object_id,
            pc_id=char_id,
            action_type=action_type,
            attribute_mod=attribute_mod,
            dc=dc,
        )
    )

    # 移动到物体旁边并记录路径 / Move PC adjacent to object and record waypoints
    waypoints = _move_to_object(char_id, object_id, scene_info, pc_state_map, actor_state_map)

    # 生成交互结果旁白 / Generate interaction narration
    narration = await _generate_narration(
        pc_id=char_id,
        object_id=object_id,
        scene_info=scene_info,
        result=result.result if result else {},
        success=result.success,
        plot_brief=plot_brief,
        hints=hints or [],
        config=config,
    )

    # 存入记忆 / Store memory
    await _store_interact_memory(
        char_id, object_id, scene_obj, result.success, narration, tick, config
    )

    logger.info(
        "[interact] %s → %s : %s | narration=%s",
        char_id,
        object_id,
        "success" if result.success else "fail",
        narration[:30] if narration else "(none)",
    )
    return {
        "kind": "pc_interact",
        "pc_id": char_id,
        "object_id": object_id,
        "success": result.success,
        "result": result.result if result else {},
        "waypoints": waypoints,
        "narration": narration,
    }


async def _load_scene_object(scene_repo, object_id: str) -> SceneObject | None:
    """按 id 查询场景对象 / Fetch a scene object by id."""
    if not scene_repo or not object_id:
        return None
    all_objects = await scene_repo.load_all()
    return all_objects.get(object_id)


def _interact_requirements(obj: SceneObject | None) -> tuple[str, str, int]:
    """按对象类型 + interact_data 推断 (action_type, 检定属性, dc) /
    Infer (action_type, check ability, dc) from the object's type + interact_data.

    dc <= 0 表示无需检定，直接判定成功 / dc <= 0 means no check is required, auto success.
    """
    if obj is None:
        return "interact", "dex", 0
    data = obj.interact_data or {}
    if obj.object_type == SceneObjectType.TRAP:
        return "disarm_trap", "dex", data.get("dc", _TRAP_DC)
    if obj.object_type == SceneObjectType.DOOR:
        if data.get("locked"):
            return "break_door", "str", data.get("dc", _DOOR_DC)
        return "interact", "str", 0
    if obj.object_type == SceneObjectType.CONTAINER:
        if data.get("locked") and data.get("lock_dc", 0) > 0:
            return "pick_lock", "dex", data["lock_dc"]
        return "open_chest", "dex", 0
    return "interact", "dex", 0


async def _ability_mod_for(pc_repo, char_id: str, ability: str) -> int:
    """加载 PC 属性并计算检定加值 / Load PC attributes and compute the check bonus."""
    if not pc_repo or not char_id:
        return 0
    pc = await pc_repo.load_one(char_id)
    if not pc:
        return 0
    try:
        attrs = json.loads(pc.attributes_json or "{}")
    except (TypeError, ValueError):
        attrs = {}
    return ability_modifier(attrs.get(ability, 10))


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


async def _generate_narration(
    pc_id: str,
    object_id: str,
    scene_info: dict | None,
    result: dict,
    success: bool,
    plot_brief: str,
    hints: list[str],
    config: RunnableConfig = None,
) -> str:
    """调用 LLM 生成交互结果旁白 / Generate interaction result narration via LLM."""
    llm = get_llm(config)
    if llm is None:
        return _fallback_narration(pc_id, object_id, result, success)

    pc = _find_pc(pc_id, scene_info)
    obj = _find_scene_object(object_id, scene_info)
    scene = (scene_info or {}).get("scene", {})

    query = f"{plot_brief} {obj.get('name', '')} {scene.get('description', '')}".strip()
    memories = await retrieve_memories(pc_id, query, config=config, top_k=5)

    ctx = {
        "pc": pc,
        "obj": obj,
        "scene": scene,
        "result": result,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memories,
    }

    try:
        system = _PROMPTS.get_template("interact/_interact_system.jinja").render(**ctx)
        prompt = _PROMPTS.get_template("interact/interact_narrate.jinja").render(**ctx)
    except Exception:
        logger.exception("[interact] prompt render failed")
        return _fallback_narration(pc_id, object_id, result, success)

    try:
        raw = await llm.call_structured(
            "interact",
            InteractNarrationSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
            fallback=lambda: InteractNarrationSchema(
                narration=_fallback_narration(pc_id, object_id, result, success)
            ),
        )
        return raw.narration or _fallback_narration(pc_id, object_id, result, success)
    except Exception:
        logger.exception("[interact] narration generation failed for %s -> %s", pc_id, object_id)
        return _fallback_narration(pc_id, object_id, result, success)


def _fallback_narration(pc_id: str, object_id: str, result: dict, success: bool) -> str:
    """LLM 不可用时降级旁白 / Fallback narration."""
    action_cn = result.get("action_cn", "交互")
    status = "成功" if success else "失败"
    return f"{pc_id} 对 {object_id} 进行了{action_cn}，结果{status}。"


def _find_pc(pc_id: str, scene_info: dict | None) -> dict:
    """在 scene_info 中查找 PC 信息 / Find PC info in scene_info."""
    if not scene_info:
        return {"id": pc_id, "name": pc_id}
    for pc in scene_info.get("pcs", []):
        if pc.get("id") == pc_id:
            return pc
    return {"id": pc_id, "name": pc_id}


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

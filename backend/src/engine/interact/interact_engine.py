"""Interact Engine——场景对象交互裁决 / Scene object interaction resolution."""

import json
import logging

from langchain_core.runnables.config import RunnableConfig

from ...domain.scene_object import SceneObject, SceneObjectType
from ...rules.dnd_rules import ability_modifier, resolve_check
from ...schemas.request import SceneObjectInteractRequest
from ...schemas.response import SceneObjectInteractResponse
from ...utils.helpers import get_repo

logger = logging.getLogger("aw.eng.interact")

# object_type/interact_data → (action_type, 检定属性, 默认 dc) / → (action_type, check ability, default dc)
_TRAP_DC = 12
_DOOR_DC = 13
_LOCK_DC = 12

_ACTION_CN = {
    "pick_lock": "开锁",
    "disarm_trap": "拆陷阱",
    "break_door": "破门",
    "open_chest": "开宝箱",
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


async def process_interact_action(decision: dict, config: RunnableConfig = None) -> dict | None:
    """处理单个 interact 决策 → 按场景对象规则检定，返回原始检定结果（不构造事件）/
    Resolve a single interact decision against the target scene object's D&D rules,
    return the raw check result (not an event)."""
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
    logger.info(
        "[interact] %s → %s : %s", char_id, object_id, "success" if result.success else "fail"
    )
    return {
        "kind": "pc_interact",
        "pc_id": char_id,
        "object_id": object_id,
        "success": result.success,
        "result": result.result if result else {},
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
    pc = await pc_repo.load_pc(char_id)
    if not pc:
        return 0
    try:
        attrs = json.loads(pc.attributes_json or "{}")
    except (TypeError, ValueError):
        attrs = {}
    return ability_modifier(attrs.get(ability, 10))

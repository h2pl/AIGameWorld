"""场景对象交互——开锁/拆陷阱/破门 / Scene object interaction (locks/traps/doors)."""

from ...rules.dnd_rules import resolve_check
from ...schemas.request import SceneObjectInteractRequest
from ...schemas.response import SceneObjectInteractResponse


def resolve_interact(req: SceneObjectInteractRequest) -> SceneObjectInteractResponse:
    """对象交互检定 / Object interaction check."""
    result = resolve_check(bonus=req.attribute_mod, dc=req.dc)
    action_map = {
        "pick_lock": "开锁",
        "disarm_trap": "拆陷阱",
        "break_door": "破门",
        "open_chest": "开宝箱",
    }
    action_cn = action_map.get(req.action_type, req.action_type or "交互")
    return SceneObjectInteractResponse(
        success=result.success,
        result={
            "object_id": req.object_id,
            "character_id": req.character_id,
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

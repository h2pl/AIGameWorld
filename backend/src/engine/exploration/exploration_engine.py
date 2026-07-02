"""Exploration Engine——D20 探索检定 + 事件写入 / D20 exploration check + event writing."""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...rules.dnd_rules import resolve_check
from ...schemas.request import ExplorationRequest
from ...schemas.response import ExplorationResponse
from ...utils.helpers import get_repo

logger = logging.getLogger("aw.eng.explore")


def resolve_exploration(req: ExplorationRequest) -> ExplorationResponse:
    """探索检定——感知察觉 / Wisdom (Perception) check."""
    result = resolve_check(bonus=req.attribute_mod, dc=req.dc)
    return ExplorationResponse(
        success=result.success,
        result={
            "character_id": req.character_id,
            "action_type": req.action_type,
            "roll": result.roll,
            "bonus": req.attribute_mod,
            "dc": req.dc,
            "total": result.total,
            "critical": result.is_critical,
            "fumble": result.is_fumble,
        },
    )


async def process_explore_action(
    action: dict,
    tick_message_id: str,
    tick: int,
    config: RunnableConfig = None,
) -> None:
    """处理单个 search/explore 动作 → 检定 + 写 character_explore 事件."""
    if action.get("type") not in ("search", "explore"):
        return

    event_repo = get_repo(config, "event")
    if not event_repo or not tick_message_id:
        return

    char_id = action.get("pc_id", "")
    action_type = action.get("type", "search")
    result = resolve_exploration(ExplorationRequest(character_id=char_id, action_type=action_type))
    tick_event = {
        "type": "character_explore",
        "payload": {
            "character_id": char_id,
            "action": action_type,
            "success": result.success,
            "result": result.result if result else {},
        },
    }
    logger.info("[explore] %s %s %s", char_id, action_type, "success" if result.success else "fail")
    await event_repo.insert_tick_events(tick_message_id, tick, [tick_event])

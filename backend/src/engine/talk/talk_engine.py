"""Talk Engine——处理角色交谈动作 / Handle character talk actions.

写出 character_talk 事件到 tick_events 表。
"""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...utils.helpers import get_llm, get_repo

logger = logging.getLogger("aw.eng.talk")


async def process_talk_action(
    action: dict,
    tick_message_id: str,
    tick: int,
    config: RunnableConfig = None,
) -> None:
    """处理单个 talk 动作 → 写 character_talk 事件."""
    if action.get("type") != "talk":
        return

    event_repo = get_repo(config, "event")
    if not event_repo or not tick_message_id:
        return

    char_id = action.get("pc_id", "")
    target = action.get("target", action.get("target_id", ""))
    description = action.get("description", "")
    dialogue = description or f"{char_id} 发起交谈。"
    llm = get_llm(config)
    if llm:
        pass

    tick_event = {
        "type": "character_talk",
        "payload": {
            "character_id": char_id,
            "target_id": target,
            "dialogue": dialogue,
        },
    }
    logger.info("[talk] %s → %s : %s", char_id, target, dialogue[:60])
    await event_repo.insert_tick_events(tick_message_id, tick, [tick_event])

"""Talk Engine——处理角色交谈动作 / Handle character talk actions.

写出 character_talk 事件到 tick_events 表。
"""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...utils.helpers import get_llm, get_repo

logger = logging.getLogger("aw.eng.talk")


async def process_talk_actions(
    actions: list[dict],
    tick_message_id: str,
    tick: int,
    config: RunnableConfig = None,
) -> None:
    """处理所有 talk 动作 → 写 character_talk 事件."""
    talk_actions = [a for a in actions if a.get("type") == "talk"]
    if not talk_actions:
        return

    event_repo = get_repo(config, "event")
    if not event_repo or not tick_message_id:
        return

    tick_events: list[dict] = []
    for a in talk_actions:
        char_id = a.get("character_id", "")
        target = a.get("target", a.get("target_id", ""))
        description = a.get("description", "")
        dialogue = description or f"{char_id} 发起交谈。"
        llm = get_llm(config)
        if llm:
            # TODO: LLM 生成真实对话
            pass

        tick_events.append(
            {
                "type": "character_talk",
                "payload": {
                    "character_id": char_id,
                    "target_id": target,
                    "dialogue": dialogue,
                },
            }
        )
        logger.info("[talk] %s → %s : %s", char_id, target, dialogue[:60])

    await event_repo.insert_tick_events(tick_message_id, tick, tick_events)

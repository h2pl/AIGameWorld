"""Message Engine——创建消息，供后续节点追加事件.

Phase 0: 每个 tick 开始时创建一条消息，后续节点通过 tick_message_id + tick 写入事件.
"""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...domain.message import TickMessage
from ...schemas.request import TickMessageCreateRequest
from ...utils.helpers import get_repo

logger = logging.getLogger("aw.eng")


async def create_tick_message(req: TickMessageCreateRequest, config: RunnableConfig = None) -> str:
    """创建消息，返回 tick_message_id."""
    message_repo = get_repo(config, "message")
    if not message_repo:
        logger.warning("[msg] no message_repo")
        return ""
    tick_message_id = f"tick_{req.tick}"
    await message_repo.insert(TickMessage(id=tick_message_id, tick=req.tick, world_id=req.world_id))
    logger.info("[msg] created tick_message_id=%s tick=%s", tick_message_id, req.tick)
    return tick_message_id

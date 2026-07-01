"""Message Engine——创建消息，供后续节点追加事件.

Phase 0: 每个 tick 开始时创建一条消息，后续节点通过 msg_id + tick 写入事件.
"""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...domain.message import Message
from ...schemas.request import MessageCreateRequest
from ...utils.helpers import get_repo

logger = logging.getLogger("aw.eng")


async def create_message(req: MessageCreateRequest, config: RunnableConfig = None) -> str:
    """创建消息，返回 msg_id."""
    message_repo = get_repo(config, "message")
    if not message_repo:
        logger.warning("[msg] no message_repo")
        return ""
    msg_id = f"tick_{req.tick}"
    await message_repo.insert(Message(id=msg_id, tick=req.tick, world_id=req.world_id))
    logger.info("[msg] created msg_id=%s tick=%s", msg_id, req.tick)
    return msg_id

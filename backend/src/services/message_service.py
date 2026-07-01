"""Message Service: State ↔ Engine adapter——创建消息."""

import logging

from ..engine.message import message_engine
from ..graph.state import OverallState
from ..schemas.request import MessageCreateRequest

logger = logging.getLogger("aw.svc")


async def create_message(state: OverallState, config=None) -> dict:
    """Phase 0: 创建消息，后续节点用 msg_id 写入事件."""
    tick = state.get("tick", 0)
    world_id = state.get("world_id", "")
    logger.info("[msg] tick=%s", tick)
    msg_id = await message_engine.create_message(
        MessageCreateRequest(tick=tick, world_id=world_id), config=config
    )
    return {"msg_id": msg_id}

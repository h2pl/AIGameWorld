"""Message Service: State ↔ Engine adapter——创建消息."""

import logging

from ..engine.message import message_engine
from ..graph.state import OverallState
from ..schemas.request import TickMessageCreateRequest

logger = logging.getLogger("aw.svc")


async def create_tick_message(state: OverallState, config=None) -> dict:
    """Phase 0: 创建消息，后续节点用 tick_message_id 写入事件."""
    tick = state.get("tick", 0)
    world_id = state.get("world_id", "")
    logger.info("[msg] tick=%s", tick)
    tick_message_id = await message_engine.create_tick_message(
        TickMessageCreateRequest(tick=tick, world_id=world_id), config=config
    )
    return {"tick_message_id": tick_message_id}

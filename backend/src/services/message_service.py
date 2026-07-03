"""Message Service: State ↔ Repo adapter——创建消息.

创建消息只是一次简单的写库操作，不需要单独的 engine 层 /
Creating a message is a simple repo write, no separate engine layer is needed.
"""

from ..domain.message import TickMessage
from ..graph.state import OverallState
from ..utils.helpers import get_repo
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


@trace_node("msg.create")
async def create_tick_message(state: OverallState, config=None) -> dict:
    """Phase 0: 创建消息，后续节点用 tick_message_id 写入事件."""
    tick = state.get("tick", 0)
    world_id = state.get("world_id", "")
    logger.info("[msg] tick=%s", tick)

    message_repo = get_repo(config, "message")
    if not message_repo:
        logger.warning("[msg] no message_repo")
        return {"tick_message_id": ""}

    tick_message_id = f"tick_{tick}"
    await message_repo.insert(TickMessage(id=tick_message_id, tick=tick, world_id=world_id))
    logger.info("[msg] created tick_message_id=%s tick=%s", tick_message_id, tick)
    return {"tick_message_id": tick_message_id}

"""Talk Service: State ↔ Engine adapter——角色交谈."""

from langchain_core.runnables.config import RunnableConfig

from ..engine.talk.talk_engine import process_talk_actions
from ..graph.state import OverallState


async def process(state: OverallState, config: RunnableConfig = None) -> dict:
    """处理 talk 动作 → Engine 写 character_talk 事件."""
    await process_talk_actions(
        actions=state.get("character_actions", []),
        tick_message_id=state.get("tick_message_id", ""),
        tick=state.get("tick", 0),
        config=config,
    )
    return {}

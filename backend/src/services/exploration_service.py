"""Exploration Service: State ↔ Engine adapter——探索检定."""

from langchain_core.runnables.config import RunnableConfig

from ..engine.exploration.exploration_engine import process_explore_actions
from ..graph.state import OverallState


async def process(state: OverallState, config: RunnableConfig = None) -> dict:
    """处理 search/explore 动作 → Engine 检定 + 写 character_explore 事件."""
    await process_explore_actions(
        actions=state.get("character_actions", []),
        tick_message_id=state.get("tick_message_id", ""),
        tick=state.get("tick", 0),
        config=config,
    )
    return {}

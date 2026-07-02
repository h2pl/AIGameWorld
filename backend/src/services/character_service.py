"""Character Service: State ↔ Engine adapter——角色决策."""

from langchain_core.runnables.config import RunnableConfig

from ..engine.character.character_engine import process_characters
from ..graph.state import OverallState


async def decide(state: OverallState, config: RunnableConfig = None) -> dict:
    """加载角色 → LLM 决策 → 返回 character_actions."""
    actions = await process_characters(
        world_id=state.get("world_id", ""),
        tick=state.get("tick", 0),
        plot_brief=state.get("plot_brief", ""),
        config=config,
    )
    return {"character_actions": actions}

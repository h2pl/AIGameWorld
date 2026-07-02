"""Character Service: State ↔ Engine adapter——角色决策."""

from langchain_core.runnables.config import RunnableConfig

from ..engine.character import actor_decide as actor_engine
from ..engine.character import pc_decide as pc_engine
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


async def pc_decide(state: dict, config: RunnableConfig = None) -> dict:
    """旧版 PC service 接口 / Legacy PC service entry point."""
    actions = []
    for pc_id in state.get("pc_ids", []):
        result = await pc_engine.pc_decide(
            pc_engine.PCDecideRequest(pc_id=pc_id, plot_brief=state.get("plot_brief", ""), tick=state.get("tick", 0)),
            config,
        )
        actions.append({"character_id": result.character_id, "type": result.type, "description": result.description})
    return {"character_actions": actions}


async def actor_decide(state: dict, config: RunnableConfig = None) -> dict:
    """旧版 Actor service 接口 / Legacy Actor service entry point."""
    actions = []
    for actor_id in state.get("actor_ids", []):
        result = await actor_engine.actor_decide(
            actor_engine.ActorDecideRequest(actor_id=actor_id, plot_brief=state.get("plot_brief", ""), tick=state.get("tick", 0)),
            config,
        )
        actions.append({"character_id": result.character_id, "type": result.type, "description": result.description})
    return {"character_actions": actions}

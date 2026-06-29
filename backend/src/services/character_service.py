"""Character Service: State ↔ Engine adapter.

Service 只管 State↔Request↔Response，所有外部资源 Engine 自己从 config 取。
"""

from langchain_core.runnables.config import RunnableConfig

from ..engine.character import actor_decide as actor_engine
from ..engine.character import pc_decide as pc_engine
from ..graph.state import CharacterSubState
from ..schemas.request import ActorDecideRequest, PCDecideRequest


async def pc_decide(state: CharacterSubState, config: RunnableConfig = None) -> dict:
    """Phase 3: 遍历 featured PCs，串行调用 LLM 决策."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []
    for pc_id in direction.get("featured_pcs", []):
        action = await pc_engine.pc_decide(
            PCDecideRequest(pc_id=pc_id, plot_brief=plot_brief, tick=tick),
            config=config,
        )
        if action:
            actions.append(action.model_dump())
    return {"character_actions": actions}


async def actor_decide(state: CharacterSubState, config: RunnableConfig = None) -> dict:
    """Phase 3: 遍历 featured Actors，串行调用 LLM 决策."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []
    for actor_id in direction.get("featured_actors", []):
        action = await actor_engine.actor_decide(
            ActorDecideRequest(actor_id=actor_id, plot_brief=plot_brief, tick=tick),
            config=config,
        )
        if action:
            actions.append(action.model_dump())
    return {"character_actions": actions}

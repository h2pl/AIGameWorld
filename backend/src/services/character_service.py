"""Character Service: State ↔ Engine adapter."""

from ..schemas.request import PCDecideRequest, ActorDecideRequest
from ..engine.character import pc_decide as pc_engine
from ..engine.character import actor_decide as actor_engine
from ..graph.state import CharacterSubState


def pc_decide(state: CharacterSubState) -> dict:
    """Phase 3: 处理所有 featured PC 决策."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []
    for pc_id in direction.get("featured_pcs", []):
        action = pc_engine.pc_decide(PCDecideRequest(pc_id=pc_id, plot_brief=plot_brief, tick=tick))
        if action:
            actions.append(action.model_dump())
    return {"character_actions": actions}


def actor_decide(state: CharacterSubState) -> dict:
    """Phase 3: 处理所有 featured Actor 决策."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []
    for actor_id in direction.get("featured_actors", []):
        action = actor_engine.actor_decide(ActorDecideRequest(actor_id=actor_id, plot_brief=plot_brief, tick=tick))
        if action:
            actions.append(action.model_dump())
    return {"character_actions": actions}

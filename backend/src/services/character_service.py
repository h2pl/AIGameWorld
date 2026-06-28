"""Character Service: State ↔ Engine adapter."""
from typing import Any
from ..models.io.character import PCDecideInput, ActorDecideInput
from ..engine.character.pc_decide import pc_decide as _pc_decide
from ..engine.character.actor_decide import actor_decide as _actor_decide
from ..graph.state import CharacterSubState


def pc_decide(state: CharacterSubState) -> dict[str, Any]:
    """Phase 3: 处理所有 featured PC 决策."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []
    for pc_id in direction.get("featured_pcs", []):
        action = _pc_decide(PCDecideInput(pc_id=pc_id, plot_brief=plot_brief, tick=tick))
        if action:
            actions.append(action.model_dump())
    return {"character_actions": actions}


def actor_decide(state: CharacterSubState) -> dict[str, Any]:
    """Phase 3: 处理所有 featured Actor 决策."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []
    for actor_id in direction.get("featured_actors", []):
        action = _actor_decide(ActorDecideInput(actor_id=actor_id, plot_brief=plot_brief, tick=tick))
        if action:
            actions.append(action.model_dump())
    return {"character_actions": actions}

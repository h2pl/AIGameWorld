"""Character Service: State ↔ Engine adapter."""
from typing import Any
from ..models.character import PCDecideInput, ActorDecideInput
from ..engine.character.pc_decide import pc_decide as _pc_decide
from ..engine.character.actor_decide import actor_decide as _actor_decide
from ..graph.state import CharacterSubState


def _to_pc_input(state: CharacterSubState, pc_id: str) -> PCDecideInput:
    """① State → Engine 输入（per-PC）"""
    return {"pc_id": pc_id, "plot_brief": state.get("plot_brief", ""), "tick": state.get("tick", 0)}


def _to_actor_input(state: CharacterSubState, actor_id: str) -> ActorDecideInput:
    """① State → Engine 输入（per-Actor）"""
    return {"actor_id": actor_id, "plot_brief": state.get("plot_brief", ""), "tick": state.get("tick", 0)}


def pc_decide(state: CharacterSubState) -> dict[str, Any]:
    """Phase 3: 处理所有 featured PC 决策. 产出 / Outputs: character_actions"""
    direction = state.get("scene_direction", {})
    actions = []
    for pc_id in direction.get("featured_pcs", []):
        action = _pc_decide(_to_pc_input(state, pc_id))
        if action:
            actions.append(action)
    return {"character_actions": actions}


def actor_decide(state: CharacterSubState) -> dict[str, Any]:
    """Phase 3: 处理所有 featured Actor 决策. 产出 / Outputs: character_actions"""
    direction = state.get("scene_direction", {})
    actions = []
    for actor_id in direction.get("featured_actors", []):
        action = _actor_decide(_to_actor_input(state, actor_id))
        if action:
            actions.append(action)
    return {"character_actions": actions}

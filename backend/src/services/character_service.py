"""Character Service: PC + Actor decision adapter / 角色服务：PC + Actor 决策适配。"""
from typing import Any
from ..engine.character.pc_decide import pc_decide as _pc_decide
from ..engine.character.actor_decide import actor_decide as _actor_decide
from ..graph.state import CharacterSubState


def pc_decide(state: CharacterSubState) -> dict[str, Any]:
    """Phase 3: 处理所有 featured PC 决策 / All featured PCs decide.

    graph State → [pc_decide()] → graph State keys.
    产出 / Outputs: character_actions (add reducer)
    """
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []

    for pc_id in direction.get("featured_pcs", []):
        action = _pc_decide(pc_id=pc_id, plot_brief=plot_brief, tick=tick)
        if action:
            actions.append(action)

    return {"character_actions": actions}


def actor_decide(state: CharacterSubState) -> dict[str, Any]:
    """Phase 3: 处理所有 featured Actor 决策 / All featured Actors decide.

    graph State → [actor_decide()] → graph State keys.
    产出 / Outputs: character_actions (add reducer)
    """
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []

    for actor_id in direction.get("featured_actors", []):
        action = _actor_decide(actor_id=actor_id, plot_brief=plot_brief, tick=tick)
        if action:
            actions.append(action)

    return {"character_actions": actions}

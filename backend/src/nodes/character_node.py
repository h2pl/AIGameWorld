"""Character Node: PC + Actor decision / 角色节点：PC + Actor 决策。"""
from typing import Any
from ..engine.character.pc_decide import pc_decide
from ..engine.character.actor_decide import actor_decide


def pc_decide_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 3: PC 决策 / PC decides action.

    产出 / Outputs: action_out
    """
    action = pc_decide(
        pc_id=state.get("pc_id", ""),
        plot_brief=state.get("plot_brief", ""),
        tick=state.get("tick", 0),
    )
    return {"action_out": action}


def actor_decide_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 3: Actor 决策 / Actor decides action.

    产出 / Outputs: action_out
    """
    action = actor_decide(
        actor_id=state.get("actor_id", ""),
        plot_brief=state.get("plot_brief", ""),
        tick=state.get("tick", 0),
    )
    return {"action_out": action}

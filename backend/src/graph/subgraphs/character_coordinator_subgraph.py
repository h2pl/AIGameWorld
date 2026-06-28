"""Phase 3 协调子图: 唤醒 PC + Actor 决策。"""
from typing import Any

from langgraph.graph import StateGraph, END

from ...nodes.character_nodes import pc_decide_node, actor_decide_node


def _character_decide(state: dict[str, Any]) -> dict[str, Any]:
    """唤醒 DM 指定的 PC + Actor，收集 actions。
    后续 M5 改为 Send fan-out 并行。
    """
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    actions = []

    for pc_id in direction.get("featured_pcs", []):
        r = pc_decide_node({"pc_id": pc_id, "plot_brief": plot_brief})
        if r.get("action_out"):
            actions.append(r["action_out"])

    for actor_id in direction.get("featured_actors", []):
        r = actor_decide_node({"actor_id": actor_id, "plot_brief": plot_brief})
        if r.get("action_out"):
            actions.append(r["action_out"])

    return {"character_actions": actions}


def build_character_coordinator_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("character_decide", _character_decide)
    graph.set_entry_point("character_decide")
    graph.add_edge("character_decide", END)
    return graph


character_coordinator_subgraph = build_character_coordinator_subgraph().compile()

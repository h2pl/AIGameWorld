"""Phase 3 协调子图: 唤醒 PC + Actor 决策 / Character coordination subgraph.

这个子图不调用 engine/，而是协调已有的 pc/actor 子图。
It coordinates existing pc/actor subgraphs, not engine services.
"""
from typing import Any

from langgraph.graph import StateGraph, END

from .character_subgraph import pc_subgraph, actor_subgraph


def _character_decide_coordinator(state: dict[str, Any]) -> dict[str, Any]:
    """唤醒 DM 指定的 PC + Actor，收集 actions。

    后续 M5 改为 Send fan-out 并行 / Future M5: Send fan-out.
    """
    direction = state.get("scene_direction", {})
    featured_pcs = direction.get("featured_pcs", [])
    featured_actors = direction.get("featured_actors", [])
    plot_brief = state.get("plot_brief", "")

    actions = []

    for pc_id in featured_pcs:
        pc_input = {"pc_id": pc_id, "plot_brief": plot_brief}
        result = pc_subgraph.invoke(pc_input)
        if result.get("action_out"):
            actions.append(result["action_out"])

    for actor_id in featured_actors:
        actor_input = {"actor_id": actor_id, "plot_brief": plot_brief}
        result = actor_subgraph.invoke(actor_input)
        if result.get("action_out"):
            actions.append(result["action_out"])

    return {"character_actions": actions}


def build_character_coordinator_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("character_decide", _character_decide_coordinator)
    graph.set_entry_point("character_decide")
    graph.add_edge("character_decide", END)
    return graph


character_coordinator_subgraph = build_character_coordinator_subgraph().compile()

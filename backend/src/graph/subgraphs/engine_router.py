"""Phase 4 协调子图: 路由到各 Engine / Engine router subgraph.

这个子图不调用 engine/，而是协调已有的 combat/dialogue/exploration/quest 子图。
"""
from typing import Any

from langgraph.graph import StateGraph, END

from .combat_subgraph import combat_subgraph
from .dialogue_subgraph import dialogue_subgraph
from .exploration_subgraph import exploration_subgraph
from .quest_subgraph import quest_subgraph


def _engine_router_node(state: dict[str, Any]) -> dict[str, Any]:
    """条件路由到各 Engine 子图 / Route to engine subgraphs.

    当前全部 invoke（mock 返回空）/ Currently invokes all engines.
    后续 M6 按 Action type 条件路由 / Future M6: conditional routing by Action type.
    """
    results = []

    combat_result = combat_subgraph.invoke({"participants": [], "round": 1})
    results.append({"engine": "combat", "result": combat_result.get("result")})

    dialogue_result = dialogue_subgraph.invoke({"speaker": "", "target": "", "intent": ""})
    results.append({"engine": "dialogue", "result": dialogue_result.get("check_result")})

    explore_result = exploration_subgraph.invoke({"character_id": "", "action_type": ""})
    results.append({"engine": "exploration", "result": explore_result.get("check_result")})

    quest_result = quest_subgraph.invoke({"quests": [], "event_log": []})
    results.append({"engine": "quest", "completed": quest_result.get("completed_quests", [])})

    return {
        "engine_results": results,
        "combat_result": combat_result.get("result"),
    }


def build_engine_router_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("engine_router", _engine_router_node)
    graph.set_entry_point("engine_router")
    graph.add_edge("engine_router", END)
    return graph


engine_router_subgraph = build_engine_router_subgraph().compile()

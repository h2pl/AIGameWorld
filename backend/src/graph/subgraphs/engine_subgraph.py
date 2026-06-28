"""Phase 4 子图: 路由到各 Engine。"""
from typing import Any

from langgraph.graph import StateGraph, END

from ...nodes.combat_nodes import combat_node
from ...nodes.dialogue_nodes import dialogue_node
from ...nodes.exploration_nodes import exploration_node
from ...nodes.quest_nodes import quest_node


def _engine_route(state: dict[str, Any]) -> dict[str, Any]:
    """条件路由到各 Engine。后续 M6 按 Action type 条件路由。"""
    results = []

    cr = combat_node({"participants": [], "round": 1})
    results.append({"engine": "combat", "result": cr.get("result")})

    dr = dialogue_node({"speaker": "", "target": "", "intent": ""})
    results.append({"engine": "dialogue", "result": dr.get("check_result")})

    er = exploration_node({"character_id": "", "action_type": ""})
    results.append({"engine": "exploration", "result": er.get("check_result")})

    qr = quest_node({"quests": [], "event_log": []})
    results.append({"engine": "quest", "completed": qr.get("completed_quests", [])})

    return {"engine_results": results, "combat_result": cr.get("result")}


def build_engine_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("engine_route", _engine_route)
    graph.set_entry_point("engine_route")
    graph.add_edge("engine_route", END)
    return graph


engine_subgraph = build_engine_subgraph().compile()

"""CombatEngine 子图 / Combat Engine Subgraph — compiled StateGraph.

Phase 4: 回合制战斗 / Turn-based combat.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class CombatSubState(TypedDict):
    """CombatEngine 子图状态 / CombatEngine subgraph state."""
    participants: list[str]
    round: int
    result: dict[str, Any] | None


def resolve_combat_node(state: CombatSubState) -> dict:
    """战斗裁决 / Combat resolution.
    
    Mock: 空结果 / Empty result.
    后续 M6 接入 DndRules / M6: DndRules integration.
    """
    return {"result": None}


def build_combat_subgraph() -> StateGraph:
    """构建 Combat 子图 / Build Combat subgraph."""
    graph = StateGraph(CombatSubState)
    graph.add_node("resolve", resolve_combat_node)
    graph.set_entry_point("resolve")
    graph.add_edge("resolve", END)
    return graph


combat_subgraph = build_combat_subgraph().compile()

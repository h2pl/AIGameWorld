"""Combat Engine Subgraph / 战斗引擎子图."""
from langgraph.graph import StateGraph, END
from ...engine.combat.combat import CombatSubState, resolve_combat_node

def build_combat_subgraph() -> StateGraph:
    graph = StateGraph(CombatSubState)
    graph.add_node("combat_resolve", resolve_combat_node)
    graph.set_entry_point("combat_resolve")
    graph.add_edge("combat_resolve", END)
    return graph

combat_subgraph = build_combat_subgraph().compile()

"""Exploration Engine Subgraph / 探索引擎子图."""
from langgraph.graph import StateGraph, END
from ...engine.exploration.exploration import ExplorationSubState, resolve_exploration_node

def build_exploration_subgraph() -> StateGraph:
    graph = StateGraph(ExplorationSubState)
    graph.add_node("exploration_process", resolve_exploration_node)
    graph.set_entry_point("exploration_process")
    graph.add_edge("exploration_process", END)
    return graph

exploration_subgraph = build_exploration_subgraph().compile()

"""Reflection Subgraph / 角色反思子图."""
from langgraph.graph import StateGraph, END
from ...engine.reflection.reflection import ReflectionSubState, reflect_node

def build_reflection_subgraph() -> StateGraph:
    graph = StateGraph(ReflectionSubState)
    graph.add_node("reflect", reflect_node)
    graph.set_entry_point("reflect")
    graph.add_edge("reflect", END)
    return graph

reflection_subgraph = build_reflection_subgraph().compile()

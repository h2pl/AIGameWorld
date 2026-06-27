"""World Engine Subgraph / 世界引擎子图."""
from langgraph.graph import StateGraph, END
from ...engine.world.world import WorldEngineSubState, execute_instructions

def build_world_subgraph() -> StateGraph:
    graph = StateGraph(WorldEngineSubState)
    graph.add_node("world_update", execute_instructions)
    graph.set_entry_point("world_update")
    graph.add_edge("world_update", END)
    return graph

world_engine_subgraph = build_world_subgraph().compile()

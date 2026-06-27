"""DM Subgraph: 双节点 StateGraph / DM subgraph with create + narrate nodes."""
from langgraph.graph import StateGraph, END
from ...engine.dm.dm import DMSubState, dm_create_node, dm_narrate_node, dm_route

def build_dm_subgraph() -> StateGraph:
    graph = StateGraph(DMSubState)
    graph.add_node("dm_create", dm_create_node)
    graph.add_node("dm_narrate", dm_narrate_node)
    graph.set_entry_point("dm_create")
    graph.add_conditional_edges("dm_create", dm_route, {
        "dm_narrate": "dm_narrate",
        "dm_create": END,
    })
    graph.add_edge("dm_narrate", END)
    return graph

dm_subgraph = build_dm_subgraph().compile()

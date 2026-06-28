"""TickGraph 主图：7 Phase 编排 — node + subgraph 混合。

Phase 1/2/5/6: plain node（单步），Phase 3/4/7: subgraph（多步协调）。
"""

from langgraph.graph import StateGraph, END

from .state import OverallState

# Phase 1/2/5/6: plain node — 单步读 State → 调 Service → 写 State
from ..nodes.dm_nodes import dm_create_node, dm_narrate_node
from ..nodes.world_nodes import world_update_node
from ..nodes.state_update_nodes import state_update_node

# Phase 3/4/7: subgraph — 含内部协调逻辑
from .subgraphs.character_coordinator import character_coordinator_subgraph
from .subgraphs.engine_router import engine_router_subgraph
from .subgraphs.reflection_coordinator import reflection_coordinator_subgraph


def build_tick_graph() -> StateGraph:
    """构建 7 Phase TickGraph。"""
    graph = StateGraph(OverallState)

    graph.add_node("phase1_dm_create", dm_create_node)
    graph.add_node("phase2_world", world_update_node)
    graph.add_node("phase3_char_decide", character_coordinator_subgraph)
    graph.add_node("phase4_engines", engine_router_subgraph)
    graph.add_node("phase5_update", state_update_node)
    graph.add_node("phase6_narrate", dm_narrate_node)
    graph.add_node("phase7_reflect", reflection_coordinator_subgraph)

    graph.set_entry_point("phase1_dm_create")
    graph.add_edge("phase1_dm_create", "phase2_world")
    graph.add_edge("phase2_world", "phase3_char_decide")
    graph.add_edge("phase3_char_decide", "phase4_engines")
    graph.add_edge("phase4_engines", "phase5_update")
    graph.add_edge("phase5_update", "phase6_narrate")

    graph.add_conditional_edges(
        "phase6_narrate",
        lambda s: "phase7_reflect" if s.get("needs_reflection") else END,
    )
    graph.add_edge("phase7_reflect", END)

    return graph


graph = build_tick_graph().compile()

"""TickGraph 主图：7 Phase StateGraph 编排 — 纯子图连线，零 wrapper。

基于 design/03-orchestration-layer.md §5 / Based on orchestration layer design.
全部 7 个 Phase 以 subgraph-as-node 挂载，主图不含任何业务逻辑。
"""

from langgraph.graph import StateGraph, END

from .state import OverallState

from .subgraphs.dm_subgraph import dm_create_subgraph, dm_narrate_subgraph
from .subgraphs.world_subgraph import world_subgraph
from .subgraphs.character_coordinator import character_coordinator_subgraph
from .subgraphs.engine_router import engine_router_subgraph
from .subgraphs.state_update_subgraph import state_update_subgraph
from .subgraphs.reflection_coordinator import reflection_coordinator_subgraph


def build_tick_graph() -> StateGraph:
    """构建 7 Phase TickGraph — 全部子图作为节点。"""
    graph = StateGraph(OverallState)

    graph.add_node("phase1_dm_create", dm_create_subgraph)
    graph.add_node("phase2_world", world_subgraph)
    graph.add_node("phase3_char_decide", character_coordinator_subgraph)
    graph.add_node("phase4_engines", engine_router_subgraph)
    graph.add_node("phase5_update", state_update_subgraph)
    graph.add_node("phase6_narrate", dm_narrate_subgraph)
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

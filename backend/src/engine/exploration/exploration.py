"""Engine exploration logic / exploration 业务逻辑.

基于 design/03-orchestration-layer.md / Based on orchestration layer design.
"""

"""ExplorationEngine 子图 / Exploration Engine Subgraph — compiled StateGraph.

Phase 4: 移动/交互检定 / Movement/interaction check.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class ExplorationSubState(TypedDict):
    """ExplorationEngine 子图状态 / ExplorationEngine subgraph state."""
    character_id: str
    action_type: str
    check_result: dict[str, Any]


def resolve_exploration_node(state: ExplorationSubState) -> dict:
    """探索检定 / Exploration check.
    
    Mock: 空检定 / Empty check.
    """
    return {"check_result": {}}


def build_exploration_subgraph() -> StateGraph:
    """构建 Exploration 子图 / Build Exploration subgraph."""
    graph = StateGraph(ExplorationSubState)
    graph.add_node("resolve", resolve_exploration_node)
    graph.set_entry_point("resolve")
    graph.add_edge("resolve", END)
    return graph


exploration_subgraph = build_exploration_subgraph().compile()

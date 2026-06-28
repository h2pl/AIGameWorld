"""Phase 5 子图: 合并结果、更新状态 / State update subgraph."""
from typing import Any

from langgraph.graph import StateGraph, END


def _state_update_node(state: dict[str, Any]) -> dict[str, Any]:
    """合并所有 Phase 结果，产出 state_diff + cast_changes。

    后续接入 WorldStateStore 写入 / Future: write via WorldStateStore.
    """
    return {"state_diff": {}, "cast_changes": []}


def build_state_update_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("state_update", _state_update_node)
    graph.set_entry_point("state_update")
    graph.add_edge("state_update", END)
    return graph


state_update_subgraph = build_state_update_subgraph().compile()

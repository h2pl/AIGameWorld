"""Phase 3 子图: 角色决策——处理 character_move / character_talk / character_explore 事件."""

from langgraph.graph import END, StateGraph

from ..state import OverallState


def _process(state: OverallState) -> dict:
    """Placeholder: 后续实现角色决策并写入 character_* 事件到 events 表."""
    return {"character_actions": []}


def build_character_subgraph() -> StateGraph:
    graph = StateGraph(OverallState)
    graph.add_node("_process", _process)
    graph.set_entry_point("_process")
    graph.add_edge("_process", END)
    return graph


character_subgraph = build_character_subgraph().compile()

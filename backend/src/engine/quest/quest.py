"""Engine quest logic / quest 业务逻辑.

基于 design/03-orchestration-layer.md / Based on orchestration layer design.
"""

"""QuestEngine 子图 / Quest Engine Subgraph — compiled StateGraph.

Phase 4: 每 Tick 检查任务完成 / Per-tick quest completion check.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class QuestSubState(TypedDict):
    """QuestEngine 子图状态 / QuestEngine subgraph state."""
    quests: list[dict[str, Any]]
    event_log: list[dict[str, Any]]
    completed_quests: list[str]


def check_quests_node(state: QuestSubState) -> dict:
    """检查任务完成 / Check quest completion.
    
    Mock: 空完成列表 / Empty completion list.
    """
    return {"completed_quests": []}


def build_quest_subgraph() -> StateGraph:
    """构建 Quest 子图 / Build Quest subgraph."""
    graph = StateGraph(QuestSubState)
    graph.add_node("check", check_quests_node)
    graph.set_entry_point("check")
    graph.add_edge("check", END)
    return graph


quest_subgraph = build_quest_subgraph().compile()

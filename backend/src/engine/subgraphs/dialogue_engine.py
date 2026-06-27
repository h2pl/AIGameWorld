"""DialogueEngine 子图 / Dialogue Engine Subgraph — compiled StateGraph.

Phase 4: D20 对话检定 / D20 dialogue check.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class DialogueSubState(TypedDict):
    """DialogueEngine 子图状态 / DialogueEngine subgraph state."""
    speaker: str
    target: str
    intent: str
    check_result: dict[str, Any]


def resolve_dialogue_node(state: DialogueSubState) -> dict:
    """对话检定 / Dialogue check.
    
    Mock: 空检定 / Empty check.
    """
    return {"check_result": {}}


def build_dialogue_subgraph() -> StateGraph:
    """构建 Dialogue 子图 / Build Dialogue subgraph."""
    graph = StateGraph(DialogueSubState)
    graph.add_node("resolve", resolve_dialogue_node)
    graph.set_entry_point("resolve")
    graph.add_edge("resolve", END)
    return graph


dialogue_subgraph = build_dialogue_subgraph().compile()

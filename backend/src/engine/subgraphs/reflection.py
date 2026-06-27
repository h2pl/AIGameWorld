"""CharacterReflection 子图 / Character Reflection Subgraph — compiled StateGraph.

Phase 7: 角色反思 / Character reflection.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class ReflectionSubState(TypedDict):
    """反思子图状态 / Reflection subgraph state."""
    character_id: str
    memories: list[dict[str, Any]]
    insight_out: str


def reflect_node(state: ReflectionSubState) -> dict:
    """角色反思 / Character reflection.
    
    Mock: 空洞察 / Empty insight.
    """
    return {"insight_out": ""}


def build_reflection_subgraph() -> StateGraph:
    """构建 Reflection 子图 / Build Reflection subgraph."""
    graph = StateGraph(ReflectionSubState)
    graph.add_node("reflect", reflect_node)
    graph.set_entry_point("reflect")
    graph.add_edge("reflect", END)
    return graph


reflection_subgraph = build_reflection_subgraph().compile()

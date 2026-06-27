"""Engine world logic / world 业务逻辑.

基于 design/03-orchestration-layer.md / Based on orchestration layer design.
"""

"""WorldEngine 子图 / World Engine Subgraph — compiled StateGraph.

Phase 2: 执行 DM 指令 / Execute DM instructions.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class WorldEngineSubState(TypedDict):
    """WorldEngine 子图状态 / WorldEngine subgraph state."""
    tick: int
    dm_instructions: list[dict[str, Any]]
    events_out: list[dict[str, Any]]  # 世界变化事件 / World change events


def execute_instructions(state: WorldEngineSubState) -> dict:
    """执行 DM 指令: 场景实例化, Actor 动机注入, 环境变化 / Execute DM instructions.
    
    Mock: 空事件 / Empty events.
    后续 M6 接入场景模板实例化 / M6: scene template instantiation.
    """
    return {"events_out": []}


def build_world_engine_subgraph() -> StateGraph:
    """构建 WorldEngine 子图 / Build WorldEngine subgraph."""
    graph = StateGraph(WorldEngineSubState)
    graph.add_node("execute", execute_instructions)
    graph.set_entry_point("execute")
    graph.add_edge("execute", END)
    return graph


world_engine_subgraph = build_world_engine_subgraph().compile()

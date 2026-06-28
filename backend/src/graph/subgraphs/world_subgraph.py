"""World Engine Subgraph / 世界引擎子图.

子图以 subgraph-as-node 形式挂入主图, Schema 使用 plain dict;
内部业务节点仍保持 WorldEngineSubState, 由 adapter 节点做 dict <-> WorldEngineSubState 转换.
这样可以避免将 OverallState 的 Annotated/reducer 元数据带入子图 checkpoint.
"""
from typing import Any

from langgraph.graph import StateGraph, END

from ...engine.world.world import WorldEngineSubState, execute_instructions


def _world_update_adapter(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 2 adapter: dict -> WorldEngineSubState -> dict (OverallState keys).

    产出 / Outputs: world_events
    """
    sub_state: WorldEngineSubState = {
        "tick": state.get("tick", 0),
        "dm_instructions": state.get("dm_instructions", []),
        "events_out": [],
    }
    result = execute_instructions(sub_state)
    return {"world_events": result.get("events_out", [])}


def build_world_subgraph() -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("world_update", _world_update_adapter)
    graph.set_entry_point("world_update")
    graph.add_edge("world_update", END)
    return graph


world_subgraph = build_world_subgraph().compile()

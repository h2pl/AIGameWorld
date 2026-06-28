"""DM Subgraphs: create + narrate 两个独立子图 / Two separate DM subgraphs.

Phase 1 调用 dm_create_subgraph, Phase 6 调用 dm_narrate_subgraph.
单入口+条件路由无法区分两个 Phase 的语义, 改为两个独立子图.

子图以 subgraph-as-node 形式挂入主图, Schema 使用 plain dict;
内部业务节点仍保持 DMSubState, 由 adapter 节点做 dict <-> DMSubState 转换.
这样可以避免将 OverallState 的 Annotated/reducer 元数据带入子图 checkpoint.
"""
from typing import Any

from langgraph.graph import StateGraph, END

from ...engine.dm.dm import (
    DMSubState, dm_create_node, dm_narrate_node,
)


def _build_dm_substate(state: dict[str, Any]) -> DMSubState:
    """从主图 plain dict 构造 DMSubState / Build DMSubState from dict."""
    return {
        "tick": state.get("tick", 0),
        "plot_brief": state.get("plot_brief", ""),
        "instructions_out": [],
        "scene_direction": {},
        "narrative_out": "",
        "character_actions": state.get("character_actions", []),
    }


def _dm_create_adapter(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 1 adapter: dict -> DMSubState -> dict (OverallState keys).

    产出 / Outputs: dm_instructions, plot_brief, scene_direction
    """
    sub_state = _build_dm_substate(state)
    result = dm_create_node(sub_state)
    return {
        "dm_instructions": result.get("instructions_out", []),
        "plot_brief": result.get("plot_brief", ""),
        "scene_direction": result.get("scene_direction", {}),
    }


def _dm_narrate_adapter(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 6 adapter: dict -> DMSubState -> dict (OverallState keys).

    产出 / Outputs: narrative, needs_reflection
    """
    sub_state = _build_dm_substate(state)
    result = dm_narrate_node(sub_state)
    return {
        "narrative": result.get("narrative_out", ""),
        "needs_reflection": state.get("tick", 0) % 5 == 0,
    }


def build_dm_create_subgraph() -> StateGraph:
    """Phase 1: DM 创造情境 / DM creates context."""
    graph = StateGraph(dict)
    graph.add_node("dm_create", _dm_create_adapter)
    graph.set_entry_point("dm_create")
    graph.add_edge("dm_create", END)
    return graph


def build_dm_narrate_subgraph() -> StateGraph:
    """Phase 6: DM 叙事 / DM narrates."""
    graph = StateGraph(dict)
    graph.add_node("dm_narrate", _dm_narrate_adapter)
    graph.set_entry_point("dm_narrate")
    graph.add_edge("dm_narrate", END)
    return graph


dm_create_subgraph = build_dm_create_subgraph().compile()
dm_narrate_subgraph = build_dm_narrate_subgraph().compile()

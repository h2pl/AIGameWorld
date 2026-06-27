"""Engine dm logic / dm 业务逻辑.

基于 design/03-orchestration-layer.md / Based on orchestration layer design.
"""

"""DM Agent 子图 / DM Agent Subgraph — compiled StateGraph.

Phase 1 (create context) / Phase 6 (narrate).
不同入口调用同一个 compile，输入不同 / Same compile, different inputs per phase.
"""

from typing import TypedDict, Any

from langgraph.graph import StateGraph, END


class DMSubState(TypedDict):
    """DM 子图状态 / DM subgraph state."""
    tick: int
    plot_brief: str
    instructions_out: list[dict[str, Any]]
    scene_direction: dict[str, Any]
    narrative_out: str
    character_actions: list[dict[str, Any]]


# ============================================================
# Phase 1 Node: 创造情境 / Create context
# ============================================================
def dm_create_node(state: DMSubState) -> dict:
    """Phase 1: DM 创造情境 / DM creates context.
    
    Mock: 返回预设 plot_brief / Returns preset plot_brief.
    后续 M4 接入 LLM / M4 connects to LLM.
    """
    tick = state.get("tick", 0)
    return {
        "plot_brief": f"[Tick {tick}] The adventure continues in the Forgotten Realms.",
        "instructions_out": [],
        "scene_direction": {"featured_pcs": [], "featured_actors": []},
    }


# ============================================================
# Phase 6 Node: 叙事 / Narrate
# ============================================================
def dm_narrate_node(state: DMSubState) -> dict:
    """Phase 6: DM 基于结果叙事 / DM narrates based on results.
    
    Mock: 拼接叙事文本 / Simple concatenation.
    后续 M4 接入 LLM / M4 connects to LLM.
    """
    plot = state.get("plot_brief", "")
    actions = state.get("character_actions", [])
    narrative = f"[DM Narrative] {plot} (Actions: {len(actions)})"
    return {"narrative_out": narrative}


# ============================================================
# 构建 + compile 子图 / Build + compile subgraph
# ============================================================
def dm_route(state: DMSubState) -> str:
    """路由: 有 character_actions → 叙事模式, 无 → 创造模式.
    Route: has character_actions → narrate mode, none → create mode.
    """
    if state.get("character_actions"):
        return "dm_narrate"
    return "dm_create"


def build_dm_subgraph() -> StateGraph:
    """构建 DM 子图 / Build DM subgraph.
    两个节点: dm_create (P1) + dm_narrate (P6), 按输入自动路由.
    Two nodes: dm_create (P1) + dm_narrate (P6), auto-routed by input.
    """
    graph = StateGraph(DMSubState)
    graph.add_node("dm_create", dm_create_node)
    graph.add_node("dm_narrate", dm_narrate_node)
    graph.set_entry_point("dm_create")
    graph.add_conditional_edges("dm_create", dm_route, {
        "dm_narrate": "dm_narrate",
        "dm_create": END,
    })
    graph.add_edge("dm_narrate", END)
    return graph


dm_subgraph = build_dm_subgraph().compile()
"""DM 子图编译实例 / Compiled DM subgraph instance.
Phase 1 (create) 和 Phase 6 (narrate) 共用一个 compile, 按输入自动路由.
"""

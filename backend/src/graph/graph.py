"""TickGraph 主图：7 Phase StateGraph 编排 / Main graph: 7-phase StateGraph orchestration.

基于 design/03-orchestration-layer.md §5 / Based on orchestration layer design.
每个 Phase 节点通过 Wrapper invoke 对应子图的 compile() / Each phase invokes subgraph compile via wrapper.
"""

from typing import Any

from langgraph.graph import StateGraph, END

from .state import OverallState

from .subgraphs.dm_subgraph import dm_create_subgraph, dm_narrate_subgraph, DMSubState
from .subgraphs.world_subgraph import world_subgraph, WorldEngineSubState
from .subgraphs.character_subgraph import pc_subgraph, actor_subgraph
from .subgraphs.combat_subgraph import combat_subgraph
from .subgraphs.dialogue_subgraph import dialogue_subgraph
from .subgraphs.exploration_subgraph import exploration_subgraph
from .subgraphs.quest_subgraph import quest_subgraph
from .subgraphs.reflection_subgraph import reflection_subgraph
from .subgraphs.summarizer_subgraph import summarizer_subgraph
from ..adapters.wrappers import (
    wrap_dm_create_input, unwrap_dm_create_output,
    wrap_world_engine_input, unwrap_world_engine_output,
    wrap_dm_narrate_input, unwrap_dm_narrate_output,
)


# ============================================================
# OverallState: 主图状态 / Main graph state
# ============================================================
# ============================================================
# Phase 节点：invoke 子图 / Phase nodes: invoke subgraphs
# ============================================================

def phase1_dm_create(state: OverallState) -> dict:
    """Phase 1: invoke DM Subgraph / invoke DM subgraph.
    
    DM 子图读出 WorldState + StoryArc → plot_brief + SceneDirection.
    """
    dm_input = wrap_dm_create_input(state)
    result = dm_create_subgraph.invoke(dm_input)
    return unwrap_dm_create_output(result)


def phase2_world(state: OverallState) -> dict:
    """Phase 2: invoke WorldEngine Subgraph / invoke WorldEngine subgraph."""
    we_input = wrap_world_engine_input(state)
    result = world_subgraph.invoke(we_input)
    return unwrap_world_engine_output(result)


def phase3_character_decide(state: OverallState) -> dict:
    """Phase 3: invoke PC/Actor Subgraphs / invoke character subgraphs.
    
    后续 M5 改为 Send fan-out 并行 / Future M5: Send fan-out.
    当前串行调用所有 PC + Actor / Currently invokes all PCs + Actors sequentially.
    """
    actions = []
    featured_pcs = state.get("scene_direction", {}).get("featured_pcs", [])
    featured_actors = state.get("scene_direction", {}).get("featured_actors", [])

    # 并行调用 PC / Invoke each PC subgraph
    for pc_id in featured_pcs:
        pc_input = {"pc_id": pc_id, "plot_brief": state.get("plot_brief", "")}
        result = pc_subgraph.invoke(pc_input)
        if result.get("action_out"):
            actions.append(result["action_out"])

    # 并行调用 Actor / Invoke each Actor subgraph
    for actor_id in featured_actors:
        actor_input = {"actor_id": actor_id, "plot_brief": state.get("plot_brief", "")}
        result = actor_subgraph.invoke(actor_input)
        if result.get("action_out"):
            actions.append(result["action_out"])

    return {"character_actions": actions}


def phase4_engines(state: OverallState) -> dict:
    """Phase 4: 条件路由 invoke 对应 Engine / Conditional route to engine subgraph.
    
    当前全部 invoke（mock 返回空）/ All engines invoked (mock returns empty).
    后续 M6 按 Action type 条件路由 / Future M6: conditional routing by Action type.
    """
    results = []
    
    # Combat / 战斗引擎
    combat_result = combat_subgraph.invoke({"participants": [], "round": 1})
    results.append({"engine": "combat", "result": combat_result.get("result")})
    
    # Dialogue / 对话引擎
    dialogue_result = dialogue_subgraph.invoke({"speaker": "", "target": "", "intent": ""})
    results.append({"engine": "dialogue", "result": dialogue_result.get("check_result")})
    
    # Exploration / 探索引擎
    explore_result = exploration_subgraph.invoke({"character_id": "", "action_type": ""})
    results.append({"engine": "exploration", "result": explore_result.get("check_result")})
    
    # Quest / 任务引擎
    quest_result = quest_subgraph.invoke({"quests": [], "event_log": []})
    results.append({"engine": "quest", "completed": quest_result.get("completed_quests", [])})

    return {
        "engine_results": results,
        "combat_result": combat_result.get("result"),
    }


def phase5_state_update(state: OverallState) -> dict:
    """Phase 5: 合并所有结果 / Merge all results.
    
    后续接入 WorldStateStore 写入 / Future: write via WorldStateStore.
    """
    return {"state_diff": {}, "cast_changes": []}


def phase6_dm_narrate(state: OverallState) -> dict:
    """Phase 6: invoke DM Subgraph (narration) / invoke DM subgraph for narration."""
    dm_input = wrap_dm_narrate_input(state)
    result = dm_narrate_subgraph.invoke(dm_input)
    update = unwrap_dm_narrate_output(result)
    update["needs_reflection"] = state["tick"] % 5 == 0
    return update


def phase7_reflection(state: OverallState) -> dict:
    """Phase 7: invoke Reflection + Summarizer / invoke reflection + summarizer."""
    reflection_subgraph.invoke({"character_id": "", "memories": []})
    summarizer_subgraph.invoke({"events": [], "tick": state["tick"]})
    return {"reflected_characters": [], "summary_compressed": False}


# ============================================================
# 构建 StateGraph / Build StateGraph
# ============================================================

def build_tick_graph() -> StateGraph:
    """构建 7 Phase TickGraph / Build the 7-phase TickGraph."""
    graph = StateGraph(OverallState)

    graph.add_node("phase1_dm_create", phase1_dm_create)
    graph.add_node("phase2_world", phase2_world)
    graph.add_node("phase3_character_decide", phase3_character_decide)
    graph.add_node("phase4_engines", phase4_engines)
    graph.add_node("phase5_state_update", phase5_state_update)
    graph.add_node("phase6_dm_narrate", phase6_dm_narrate)
    graph.add_node("phase7_reflection", phase7_reflection)

    graph.set_entry_point("phase1_dm_create")
    graph.add_edge("phase1_dm_create", "phase2_world")
    graph.add_edge("phase2_world", "phase3_character_decide")
    graph.add_edge("phase3_character_decide", "phase4_engines")
    graph.add_edge("phase4_engines", "phase5_state_update")
    graph.add_edge("phase5_state_update", "phase6_dm_narrate")

    graph.add_conditional_edges(
        "phase6_dm_narrate",
        lambda s: "phase7_reflection" if s.get("needs_reflection") else END,
    )
    graph.add_edge("phase7_reflection", END)

    return graph


# 编译后的图实例（供 LangGraph Studio / langgraph.json 引用）
# Compiled graph instance for LangGraph Studio and langgraph.json
graph = build_tick_graph().compile()


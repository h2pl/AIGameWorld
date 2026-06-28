"""TickGraph 主图：7 Phase StateGraph 编排 / Main graph: 7-phase StateGraph orchestration.

基于 design/03-orchestration-layer.md §5 / Based on orchestration layer design.
Phase 1/2/6 通过 subgraph-as-node 直接挂载编译后的子图 / Phase 1/2/6 mount compiled subgraphs as nodes.

================================================================================
7 Phase 调用状态机 / 7-Phase invocation state machine
================================================================================

每个 Tick 从 Phase 1 顺序执行到 Phase 6；Phase 7 按条件触发。
Each tick runs sequentially from Phase 1 to Phase 6; Phase 7 is conditional.

  +----------------+   +----------------+   +----------------+
  | phase1         |-->| phase2         |-->| phase3         |
  | DM Create      |   | World Engine   |   | Character      |
  | 读取世界状态    |   | 生成世界事件    |   | Decide         |
  | 产出剧情简报    |   | (天气/昼夜等)   |   | PC/Actor 决策   |
  +----------------+   +----------------+   +----------------+
         |                                              |
         v                                              v
  +----------------+   +----------------+   +----------------+
  | phase4         |-->| phase5         |-->| phase6         |
  | Engines        |   | State Update   |   | DM Narrate     |
  | 战斗/对话/探索  |   | 合并结果写回    |   | 生成叙事文本    |
  /任务引擎       |   | WorldStateStore |   | 触发 reflection |
  +----------------+   +----------------+   +----------------+
                                                      |
                                    needs_reflection == True
                                                      |
                                                      v
                                               +----------------+
                                               | phase7         |
                                               | Reflection +   |
                                               | Summarizer     |
                                               | 记忆压缩/摘要   |
                                               +----------------+
                                                      |
                                                      v
                                                     END

节点职责 / Node responsibilities:
  phase1_dm_create       — subgraph-as-node: DM 创造子图 dm_create_subgraph
  phase2_world           — subgraph-as-node: WorldEngine 子图 world_subgraph
  phase3_character_decide— 调用 PC/Actor 子图，收集 character_actions
  phase4_engines         — 条件路由调用 combat/dialogue/exploration/quest 子图
  phase5_state_update    — 合并 engine_results，产出 state_diff + cast_changes
  phase6_dm_narrate      — subgraph-as-node: DM 叙事子图 dm_narrate_subgraph
  phase7_reflection      — 每 5 tick 触发一次 reflection + summarizer
================================================================================
"""

from typing import Any

from langgraph.graph import StateGraph, END

from .state import OverallState

from .subgraphs.dm_subgraph import dm_create_subgraph, dm_narrate_subgraph
from .subgraphs.world_subgraph import world_subgraph
from .subgraphs.character_subgraph import pc_subgraph, actor_subgraph
from .subgraphs.combat_subgraph import combat_subgraph
from .subgraphs.dialogue_subgraph import dialogue_subgraph
from .subgraphs.exploration_subgraph import exploration_subgraph
from .subgraphs.quest_subgraph import quest_subgraph
from .subgraphs.reflection_subgraph import reflection_subgraph
from .subgraphs.summarizer_subgraph import summarizer_subgraph


# ============================================================
# Phase 节点：Phase 3/4/5/7 暂保留 wrapper / Phase 3/4/5/7 keep wrappers for now
# ============================================================

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

    # Phase 1/2/6: 子图直接作为节点 / Subgraphs as nodes
    graph.add_node("phase1_dm_create", dm_create_subgraph)
    graph.add_node("phase2_world", world_subgraph)
    graph.add_node("phase3_character_decide", phase3_character_decide)
    graph.add_node("phase4_engines", phase4_engines)
    graph.add_node("phase5_state_update", phase5_state_update)
    graph.add_node("phase6_dm_narrate", dm_narrate_subgraph)
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

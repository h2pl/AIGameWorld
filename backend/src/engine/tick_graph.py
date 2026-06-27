"""TickGraph 主图：7 Phase StateGraph / Main graph: 7-phase StateGraph.

基于 design/03-orchestration-layer.md §5 / Based on orchestration layer design.
"""

from typing import TypedDict, Annotated, Any
from operator import add

from langgraph.graph import StateGraph, END


# ============================================================
# OverallState: 主图状态 / Main graph state
# ============================================================
class OverallState(TypedDict):
    """7 Phase 主图状态 / 7-phase main graph state."""

    # 控制 / Control
    tick: int  # 当前 tick 号 / Current tick number

    # Phase 1: DM 创造情境 / DM creates context
    dm_instructions: list[dict[str, Any]]  # DMInstruction[]
    plot_brief: str  # 剧情梗概 / Plot brief
    scene_direction: dict[str, Any]  # featured_pcs + featured_actors

    # Phase 2: WorldEngine / World engine execution
    world_events: Annotated[list[dict[str, Any]], add]

    # Phase 3: 角色决策 / Character decisions
    character_actions: Annotated[list[dict[str, Any]], add]

    # Phase 4: Engine 裁决 / Engine resolution
    engine_results: Annotated[list[dict[str, Any]], add]
    combat_result: dict[str, Any] | None  # 战斗结果 / Combat result

    # Phase 5: 状态合并 / State merge
    state_diff: dict[str, Any]  # 增量变更 / Incremental diff
    cast_changes: list[dict[str, Any]]  # 主角团变动 / Cast changes

    # Phase 6: DM 叙事 / DM narration
    narrative: str  # 最终叙事文本 / Final narrative

    # Phase 7: 反思 + 摘要 / Reflection + summary
    reflected_characters: list[str]  # 已反思角色 / Reflected character IDs
    summary_compressed: bool  # 是否触发了摘要 / Whether summary triggered

    # 控制 / Control
    errors: Annotated[list[str], add]  # 错误累积 / Error accumulator
    needs_reflection: bool  # 是否触发反思 / Whether reflection triggered


# ============================================================
# Phase 函数声明 / Phase function declarations
# 当前为 mock 实现 / Currently mock implementations
# ============================================================

def phase1_dm_create(state: OverallState) -> dict:
    """
    Phase 1: DM 创造情境 / DM creates context.
    输入 WorldState → DM Subgraph → 输出 plot_brief + SceneDirection.
    Mock: 返回预设的 plot_brief 和空指令.
    """
    return {
        "dm_instructions": [],
        "plot_brief": f"[Tick {state['tick']}] DM creates a new scene.",
        "scene_direction": {"featured_pcs": [], "featured_actors": []},
    }


def phase2_world_engine(state: OverallState) -> dict:
    """
    Phase 2: 世界引擎执行 DM 指令 / World engine executes DM instructions.
    Mock: 空事件列表.
    """
    return {"world_events": []}


def phase3_character_decide(state: OverallState) -> dict:
    """
    Phase 3: 角色决策（Send fan-out 并行）/ Character decisions (parallel fan-out).
    Mock: 空行动列表. 后续 M5 接入 PC/Actor Agent.
    """
    return {"character_actions": []}


def phase4_engines(state: OverallState) -> dict:
    """
    Phase 4: 引擎条件路由（战斗/对话/探索/任务）/ Engine conditional routing.
    Mock: 空结果.
    """
    return {
        "engine_results": [],
        "combat_result": None,
    }


def phase5_state_update(state: OverallState) -> dict:
    """
    Phase 5: 合并所有 Phase 结果 → 写入 WorldState / Merge results → write WorldState.
    Mock: 空 diff.
    """
    return {
        "state_diff": {},
        "cast_changes": [],
    }


def phase6_dm_narrate(state: OverallState) -> dict:
    """
    Phase 6: DM 基于实际结果渲染叙事 / DM narrates based on actual results.
    Mock: 简单拼接.
    """
    narrative = f"[Tick {state['tick']}] {state.get('plot_brief', '')}"
    return {
        "narrative": narrative,
        "needs_reflection": state["tick"] % 5 == 0,  # 每 5 tick 触发反思 / Reflect every 5 ticks
    }


def phase7_reflection(state: OverallState) -> dict:
    """
    Phase 7: 反思 + 摘要 / Reflection + summary.
    Mock: 标记完成.
    """
    return {
        "reflected_characters": [],
        "summary_compressed": False,
    }


# ============================================================
# 构建 StateGraph / Build StateGraph
# ============================================================

def build_tick_graph() -> StateGraph:
    """构建 7 Phase TickGraph / Build the 7-phase TickGraph."""
    graph = StateGraph(OverallState)

    # 注册 7 个节点 / Register 7 nodes
    graph.add_node("phase1_dm_create", phase1_dm_create)
    graph.add_node("phase2_world_engine", phase2_world_engine)
    graph.add_node("phase3_character_decide", phase3_character_decide)
    graph.add_node("phase4_engines", phase4_engines)
    graph.add_node("phase5_state_update", phase5_state_update)
    graph.add_node("phase6_dm_narrate", phase6_dm_narrate)
    graph.add_node("phase7_reflection", phase7_reflection)

    # 线性边 / Linear edges
    graph.set_entry_point("phase1_dm_create")
    graph.add_edge("phase1_dm_create", "phase2_world_engine")
    graph.add_edge("phase2_world_engine", "phase3_character_decide")
    graph.add_edge("phase3_character_decide", "phase4_engines")
    graph.add_edge("phase4_engines", "phase5_state_update")
    graph.add_edge("phase5_state_update", "phase6_dm_narrate")

    # 条件边: Phase6 → Phase7 或 END / Conditional: Phase6 → Phase7 or END
    graph.add_conditional_edges(
        "phase6_dm_narrate",
        lambda s: "phase7_reflection" if s.get("needs_reflection") else END,
    )
    graph.add_edge("phase7_reflection", END)

    return graph

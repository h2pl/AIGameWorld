"""全拆单节点 subgraph，改为 node 函数。"""
import pathlib
import os

base = pathlib.Path(r"E:\Projects\SimGameWorld\backend\src")

# ── 1. 建 nodes/coordinators.py ──
coordinators_content = '''"""Coordinator Nodes: Phase 3/4/7 — 协调多个子 Node。

每个 coordinator 是一个纯函数：读 State、调其他 node、合并结果、写 State。
不是 subgraph — 不含 StateGraph.compile()。
"""

from typing import Any

from .character_nodes import pc_decide_node, actor_decide_node
from .combat_nodes import combat_node
from .dialogue_nodes import dialogue_node
from .exploration_nodes import exploration_node
from .quest_nodes import quest_node
from .reflection_nodes import reflection_node
from .summarizer_nodes import summarizer_node


def phase3_character_decide(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 3: 唤醒 DM 指定的 PC + Actor 决策。

    后续 M5 改为 Send fan-out 并行 / Future M5: Send fan-out.
    """
    direction = state.get("scene_direction", {})
    featured_pcs = direction.get("featured_pcs", [])
    featured_actors = direction.get("featured_actors", [])
    plot_brief = state.get("plot_brief", "")

    actions = []

    for pc_id in featured_pcs:
        result = pc_decide_node({"pc_id": pc_id, "plot_brief": plot_brief})
        if result.get("action_out"):
            actions.append(result["action_out"])

    for actor_id in featured_actors:
        result = actor_decide_node({"actor_id": actor_id, "plot_brief": plot_brief})
        if result.get("action_out"):
            actions.append(result["action_out"])

    return {"character_actions": actions}


def phase4_engine_router(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 4: 条件路由到各 Engine。

    后续 M6 按 Action type 条件路由 / Future M6: conditional routing.
    """
    results = []

    cr = combat_node({"participants": [], "round": 1})
    results.append({"engine": "combat", "result": cr.get("result")})

    dr = dialogue_node({"speaker": "", "target": "", "intent": ""})
    results.append({"engine": "dialogue", "result": dr.get("check_result")})

    er = exploration_node({"character_id": "", "action_type": ""})
    results.append({"engine": "exploration", "result": er.get("check_result")})

    qr = quest_node({"quests": [], "event_log": []})
    results.append({"engine": "quest", "completed": qr.get("completed_quests", [])})

    return {"engine_results": results, "combat_result": cr.get("result")}


def phase7_reflection_coordinator(state: dict[str, Any]) -> dict[str, Any]:
    """Phase 7: Reflection + Summarizer 协调。"""
    reflection_node({"character_id": "", "memories": []})
    summarizer_node({"events": [], "tick": state.get("tick", 0)})
    return {"reflected_characters": [], "summary_compressed": False}
'''

(base / "nodes" / "coordinators.py").write_text(coordinators_content, encoding="utf-8")
print("1. nodes/coordinators.py created")

# ── 2. 更新 graph.py ──
graph_content = '''"""TickGraph 主图 — 7 Phase 顺序执行 + 条件分支。

START
 |
 v
 phase1_dm_create   [node]  DM 创造情境   dm_create_node
 |
 v
 phase2_world       [node]  World 引擎    world_update_node
 |
 v
 phase3_char_decide [node]  角色决策协调   phase3_character_decide
 |
 v
 phase4_engines     [node]  Engine 路由   phase4_engine_router
 |
 v
 phase5_update      [node]  状态合并更新   state_update_node
 |
 v
 phase6_narrate     [node]  DM 叙事       dm_narrate_node
 |
 +-- needs_reflection? --False--> END
 |
 True
 |
 v
 phase7_reflect     [node]  反思/摘要协调  phase7_reflection_coordinator
 |
 v
 END
"""

from langgraph.graph import StateGraph, END

from .state import OverallState

from ..nodes.dm_nodes import dm_create_node, dm_narrate_node
from ..nodes.world_nodes import world_update_node
from ..nodes.state_update_nodes import state_update_node
from ..nodes.coordinators import (
    phase3_character_decide,
    phase4_engine_router,
    phase7_reflection_coordinator,
)


def build_tick_graph() -> StateGraph:
    """构建 7 Phase TickGraph — 全部 plain node，零 subgraph。"""
    graph = StateGraph(OverallState)

    graph.add_node("phase1_dm_create", dm_create_node)
    graph.add_node("phase2_world", world_update_node)
    graph.add_node("phase3_char_decide", phase3_character_decide)
    graph.add_node("phase4_engines", phase4_engine_router)
    graph.add_node("phase5_update", state_update_node)
    graph.add_node("phase6_narrate", dm_narrate_node)
    graph.add_node("phase7_reflect", phase7_reflection_coordinator)

    graph.set_entry_point("phase1_dm_create")
    graph.add_edge("phase1_dm_create", "phase2_world")
    graph.add_edge("phase2_world", "phase3_char_decide")
    graph.add_edge("phase3_char_decide", "phase4_engines")
    graph.add_edge("phase4_engines", "phase5_update")
    graph.add_edge("phase5_update", "phase6_narrate")

    graph.add_conditional_edges(
        "phase6_narrate",
        lambda s: "phase7_reflect" if s.get("needs_reflection") else END,
    )
    graph.add_edge("phase7_reflect", END)

    return graph


graph = build_tick_graph().compile()
'''

(base / "graph" / "graph.py").write_text(graph_content, encoding="utf-8")
print("2. graph.py updated")

# ── 3. 删单节点 subgraph 文件 ──
to_delete = [
    "graph/subgraphs/dm_subgraph.py",
    "graph/subgraphs/world_subgraph.py",
    "graph/subgraphs/character_coordinator.py",
    "graph/subgraphs/character_subgraph.py",
    "graph/subgraphs/engine_router.py",
    "graph/subgraphs/combat_subgraph.py",
    "graph/subgraphs/dialogue_subgraph.py",
    "graph/subgraphs/exploration_subgraph.py",
    "graph/subgraphs/quest_subgraph.py",
    "graph/subgraphs/state_update_subgraph.py",
    "graph/subgraphs/reflection_coordinator.py",
    "graph/subgraphs/reflection_subgraph.py",
    "graph/subgraphs/summarizer_subgraph.py",
]
deleted = 0
for f in to_delete:
    p = base / f
    if p.exists():
        os.remove(p)
        deleted += 1
        print(f"   deleted: {f}")
print(f"3. {deleted} subgraph files deleted")

# ── 4. 更新 test_graph.py ──
test_content = '''"""测试 TickGraph 7 Phase 主图。全部 Phase 以 node 函数挂载。"""
import pytest

from src.graph.graph import build_tick_graph, OverallState
from src.nodes.dm_nodes import dm_create_node, dm_narrate_node
from src.nodes.world_nodes import world_update_node
from src.nodes.state_update_nodes import state_update_node
from src.nodes.coordinators import (
    phase3_character_decide,
    phase4_engine_router,
    phase7_reflection_coordinator,
)


def test_build_graph_returns_state_graph():
    assert build_tick_graph() is not None


def test_graph_can_compile():
    from langgraph.checkpoint.memory import MemorySaver
    g = build_tick_graph()
    app = g.compile(checkpointer=MemorySaver())
    assert app is not None


def test_overall_state_defaults():
    state = OverallState(
        tick=0,
        dm_instructions=[], plot_brief="", scene_direction={},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )
    assert state["tick"] == 0


@pytest.fixture
def base_state() -> OverallState:
    return OverallState(
        tick=0,
        dm_instructions=[], plot_brief="", scene_direction={},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )


def test_phase1_dm_create(base_state):
    r = dm_create_node(base_state)
    assert "dm_instructions" in r
    assert "plot_brief" in r
    assert "scene_direction" in r


def test_phase2_world(base_state):
    r = world_update_node(base_state)
    assert r["world_events"] == []


def test_phase3_char_decide(base_state):
    r = phase3_character_decide(base_state)
    assert r["character_actions"] == []


def test_phase4_engine_router(base_state):
    r = phase4_engine_router(base_state)
    assert "engine_results" in r
    assert r["combat_result"] is None


def test_phase5_state_update(base_state):
    r = state_update_node(base_state)
    assert "state_diff" in r
    assert "cast_changes" in r


def test_phase6_narrate(base_state):
    base_state["character_actions"] = [{"action": "test"}]
    r = dm_narrate_node(base_state)
    assert "narrative" in r
    assert "needs_reflection" in r


def test_phase6_reflection_trigger():
    state = OverallState(
        tick=5,
        dm_instructions=[], plot_brief="Test", scene_direction={},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )
    r = dm_narrate_node(state)
    assert r["needs_reflection"] is True


def test_phase6_no_reflection_low_tick():
    state = OverallState(
        tick=1,
        dm_instructions=[], plot_brief="Test", scene_direction={},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )
    r = dm_narrate_node(state)
    assert r["needs_reflection"] is False


def test_phase7_reflect(base_state):
    r = phase7_reflection_coordinator(base_state)
    assert "reflected_characters" in r
    assert "summary_compressed" in r


@pytest.mark.asyncio
async def test_full_tick_cycle():
    from src.engine.orchestrator import Orchestrator
    orch = Orchestrator()
    for i in range(10):
        result = await orch.run_tick()
        assert "narrative" in result
        assert result["tick"] == i
    assert orch.tick == 10


@pytest.mark.asyncio
async def test_full_tick_cycle_with_custom_state():
    from src.engine.orchestrator import Orchestrator
    orch = Orchestrator()
    state = OverallState(
        tick=0,
        dm_instructions=[], plot_brief="Custom",
        scene_direction={"featured_pcs": [], "featured_actors": []},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )
    result = await orch.run_tick(state)
    assert result["narrative"] is not None
'''

(base.parent / "tests" / "unit" / "test_graph.py").write_text(test_content, encoding="utf-8")
print("4. test_graph.py updated")
print("\nALL DONE")

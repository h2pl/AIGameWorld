import pathlib, os

base = pathlib.Path(r"E:\Projects\SimGameWorld\backend\src")

# ── graph.py ──
graph_content = '''"""TickGraph 主图 — 7 Phase 顺序执行 + 条件分支。

START
 |
 v
 phase1_dm_create   [node]      DM 创造情境   dm_create_node
 |
 v
 phase2_world       [node]      World 引擎    world_update_node
 |
 v
 phase3_char_decide [subgraph]  角色决策协调   character_coordinator_subgraph
 |
 v
 phase4_engines     [subgraph]  Engine 路由   engine_router_subgraph
 |
 v
 phase5_update      [node]      状态合并更新   state_update_node
 |
 v
 phase6_narrate     [node]      DM 叙事       dm_narrate_node
 |
 +-- needs_reflection? --False--> END
 |
 True
 |
 v
 phase7_reflect     [subgraph]  反思/摘要协调  reflection_coordinator_subgraph
 |
 v
 END
"""

from langgraph.graph import StateGraph, END

from .state import OverallState

# node（单步）
from ..nodes.dm_nodes import dm_create_node, dm_narrate_node
from ..nodes.world_nodes import world_update_node
from ..nodes.state_update_nodes import state_update_node

# subgraph（多 node 协调）
from .subgraphs.character_coordinator import character_coordinator_subgraph
from .subgraphs.engine_router import engine_router_subgraph
from .subgraphs.reflection_coordinator import reflection_coordinator_subgraph


def build_tick_graph() -> StateGraph:
    graph = StateGraph(OverallState)

    graph.add_node("phase1_dm_create", dm_create_node)
    graph.add_node("phase2_world", world_update_node)
    graph.add_node("phase3_char_decide", character_coordinator_subgraph)
    graph.add_node("phase4_engines", engine_router_subgraph)
    graph.add_node("phase5_update", state_update_node)
    graph.add_node("phase6_narrate", dm_narrate_node)
    graph.add_node("phase7_reflect", reflection_coordinator_subgraph)

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
print("1. graph.py updated")

# ── test_graph.py ──
test_content = '''"""测试 TickGraph 7 Phase 主图。"""
import pytest

from src.graph.graph import build_tick_graph, OverallState
from src.nodes.dm_nodes import dm_create_node, dm_narrate_node
from src.nodes.world_nodes import world_update_node
from src.nodes.state_update_nodes import state_update_node
from src.graph.subgraphs.character_coordinator import character_coordinator_subgraph
from src.graph.subgraphs.engine_router import engine_router_subgraph
from src.graph.subgraphs.reflection_coordinator import reflection_coordinator_subgraph


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


def test_phase2_world(base_state):
    r = world_update_node(base_state)
    assert r["world_events"] == []


def test_phase3_char_decide(base_state):
    r = character_coordinator_subgraph.invoke(base_state)
    assert r["character_actions"] == []


def test_phase4_engine_router(base_state):
    r = engine_router_subgraph.invoke(base_state)
    assert "engine_results" in r
    assert r["combat_result"] is None


def test_phase5_state_update(base_state):
    r = state_update_node(base_state)
    assert "state_diff" in r


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
    r = reflection_coordinator_subgraph.invoke(base_state)
    assert "reflected_characters" in r


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
print("2. test_graph.py updated")

# ── 删 coordinators.py ──
coordinators_path = base / "nodes" / "coordinators.py"
if coordinators_path.exists():
    os.remove(coordinators_path)
    print("3. coordinators.py deleted")

print("DONE")

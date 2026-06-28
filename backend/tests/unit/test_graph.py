"""测试 TickGraph 7 Phase 主图。全部 Phase 以 node 函数挂载。"""
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

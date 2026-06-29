"""测试 TickGraph 7 Phase 主图 / TickGraph 7-phase main graph tests."""

import pytest

from src.graph.graph import OverallState, build_tick_graph

# ── Fixtures / 测试夹具 ──
from src.graph.subgraphs.character_subgraph import character_subgraph
from src.graph.subgraphs.engine_subgraph import engine_subgraph
from src.graph.subgraphs.reflection_subgraph import reflection_subgraph
from src.services import dm_service, state_update_service, world_service

# ── 图构建 / Graph build


def test_build_graph_returns_state_graph():
    assert build_tick_graph() is not None


def test_graph_can_compile():
    from langgraph.checkpoint.memory import MemorySaver

    g = build_tick_graph()
    app = g.compile(checkpointer=MemorySaver())
    assert app is not None


# ── State 验证 / State validation


def test_overall_state_defaults():
    state = OverallState(
        tick=0,
        dm_instructions=[],
        plot_brief="",
        scene_direction={},
        world_events=[],
        character_actions=[],
        engine_results=[],
        combat_result=None,
        state_diff={},
        cast_changes=[],
        narrative="",
        branch_points=[],
        hooks_resolved=[],
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )
    assert state["tick"] == 0


@pytest.fixture
def base_state() -> OverallState:
    return OverallState(
        tick=0,
        dm_instructions=[],
        plot_brief="",
        scene_direction={},
        world_events=[],
        character_actions=[],
        engine_results=[],
        combat_result=None,
        state_diff={},
        cast_changes=[],
        narrative="",
        branch_points=[],
        hooks_resolved=[],
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )


# ── Phase 1~6 节点 / Phase 1~6 nodes


@pytest.mark.asyncio
async def test_phase1_dm_create(base_state):
    r = await dm_service.dm_create(base_state)
    assert "dm_instructions" in r
    assert "plot_brief" in r


def test_phase2_world(base_state):
    r = world_service.world_update(base_state)
    assert r["world_events"] == []


@pytest.mark.asyncio
async def test_phase3_char_decide(base_state):
    r = await character_subgraph.ainvoke(base_state)
    assert r["character_actions"] == []


def test_phase4_engine_router(base_state):
    base_state["action_type"] = "search"
    r = engine_subgraph.invoke(base_state)
    assert "engine_results" in r


def test_phase5_state_update(base_state):
    r = state_update_service.state_update(base_state)
    assert "state_diff" in r


@pytest.mark.asyncio
async def test_phase6_narrate(base_state):
    base_state["character_actions"] = [{"action": "test"}]
    r = await dm_service.dm_narrate(base_state)
    # ── Phase 7 反思 / Phase 7 reflection
    assert "narrative" in r
    assert "needs_reflection" in r


@pytest.mark.asyncio
async def test_phase6_reflection_trigger():
    state = OverallState(
        tick=5,
        dm_instructions=[],
        plot_brief="Test",
        scene_direction={},
        world_events=[],
        character_actions=[],
        engine_results=[],
        combat_result=None,
        state_diff={},
        cast_changes=[],
        narrative="",
        branch_points=[],
        hooks_resolved=[],
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )
    r = await dm_service.dm_narrate(state)
    assert r["needs_reflection"] is True


@pytest.mark.asyncio
async def test_phase6_no_reflection_low_tick():
    state = OverallState(
        tick=1,
        dm_instructions=[],
        plot_brief="Test",
        scene_direction={},
        world_events=[],
        character_actions=[],
        engine_results=[],
        combat_result=None,
        state_diff={},
        cast_changes=[],
        narrative="",
        branch_points=[],
        hooks_resolved=[],
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )
    r = await dm_service.dm_narrate(state)
    assert r["needs_reflection"] is False


@pytest.mark.asyncio
# ── 全 Tick 流程 / Full tick flow
async def test_phase7_reflect(base_state):
    r = await reflection_subgraph.ainvoke(base_state)
    assert "reflected_characters" in r


@pytest.mark.asyncio
async def test_full_tick_cycle():
    from src.graph.orchestrator import Orchestrator

    orch = Orchestrator()
    for i in range(10):
        result = await orch.run_tick()
        assert "narrative" in result
        assert result["tick"] == i
    assert orch.tick == 10


@pytest.mark.asyncio
async def test_full_tick_cycle_with_custom_state():
    from src.graph.orchestrator import Orchestrator

    orch = Orchestrator()
    state = OverallState(
        tick=0,
        dm_instructions=[],
        plot_brief="Custom",
        scene_direction={"featured_pcs": [], "featured_actors": []},
        world_events=[],
        character_actions=[],
        engine_results=[],
        combat_result=None,
        state_diff={},
        cast_changes=[],
        narrative="",
        branch_points=[],
        hooks_resolved=[],
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )
    result = await orch.run_tick(state)
    assert result["narrative"] is not None


# ── DM 服务测试 / DM service tests
# ── 完整 Tick 流程 / Full tick flow

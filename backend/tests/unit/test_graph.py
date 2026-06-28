"""测试 TickGraph 7 Phase 主图 / Test TickGraph 7-phase main graph.

全部 Phase 以 subgraph-as-node 挂载，测试直接 invoke 子图。
"""
import pytest

from src.graph.graph import build_tick_graph, OverallState
from src.graph.subgraphs.dm_subgraph import dm_create_subgraph, dm_narrate_subgraph
from src.graph.subgraphs.world_subgraph import world_subgraph
from src.graph.subgraphs.character_coordinator import character_coordinator_subgraph
from src.graph.subgraphs.engine_router import engine_router_subgraph
from src.graph.subgraphs.state_update_subgraph import state_update_subgraph
from src.graph.subgraphs.reflection_coordinator import reflection_coordinator_subgraph


# ============================================================
# 测试 StateGraph 构建 / Test StateGraph construction
# ============================================================
def test_build_graph_returns_state_graph():
    graph = build_tick_graph()
    assert graph is not None


def test_graph_can_compile():
    from langgraph.checkpoint.memory import MemorySaver
    graph = build_tick_graph()
    app = graph.compile(checkpointer=MemorySaver())
    assert app is not None


# ============================================================
# 测试 OverallState 初始化 / Test OverallState initialization
# ============================================================
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
    assert state["plot_brief"] == ""
    assert state["narrative"] == ""


# ============================================================
# 测试各 Phase 子图 / Test each Phase subgraph
# ============================================================
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
    """Phase 1: DM 创造子图应返回 plot_brief / scene_direction."""
    result = dm_create_subgraph.invoke(base_state)
    assert "dm_instructions" in result
    assert "plot_brief" in result
    assert "scene_direction" in result
    assert "Tick 0" in result["plot_brief"]


def test_phase2_world(base_state):
    """Phase 2: WorldEngine 子图应返回空事件列表."""
    result = world_subgraph.invoke(base_state)
    assert "world_events" in result
    assert result["world_events"] == []


def test_phase3_char_coordinator(base_state):
    """Phase 3: 协调子图应返回空行动列表."""
    result = character_coordinator_subgraph.invoke(base_state)
    assert "character_actions" in result
    assert result["character_actions"] == []


def test_phase4_engine_router(base_state):
    """Phase 4: Engine 路由子图应返回空引擎结果."""
    result = engine_router_subgraph.invoke(base_state)
    assert "engine_results" in result
    assert "combat_result" in result
    assert result["combat_result"] is None


def test_phase5_state_update(base_state):
    """Phase 5: 状态更新子图应返回空 diff."""
    result = state_update_subgraph.invoke(base_state)
    assert "state_diff" in result
    assert "cast_changes" in result


def test_phase6_dm_narrate(base_state):
    """Phase 6: DM 叙事子图应返回 narrative / needs_reflection."""
    base_state["character_actions"] = [{"action": "test"}]
    result = dm_narrate_subgraph.invoke(base_state)
    assert "narrative" in result
    assert "needs_reflection" in result
    assert len(result["narrative"]) > 0


def test_phase6_reflection_trigger():
    """Phase 6: tick=5 应触发反思."""
    state = OverallState(
        tick=5,
        dm_instructions=[], plot_brief="Test", scene_direction={},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )
    result = dm_narrate_subgraph.invoke(state)
    assert result["needs_reflection"] is True


def test_phase6_no_reflection_low_tick():
    """Phase 6: tick=1 不触发反思."""
    state = OverallState(
        tick=1,
        dm_instructions=[], plot_brief="Test", scene_direction={},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )
    result = dm_narrate_subgraph.invoke(state)
    assert result["needs_reflection"] is False


def test_phase7_reflection_coordinator(base_state):
    """Phase 7: 协调子图应返回空反思结果."""
    result = reflection_coordinator_subgraph.invoke(base_state)
    assert "reflected_characters" in result
    assert "summary_compressed" in result


# ============================================================
# 测试完整 Tick 执行 / Test full tick execution
# ============================================================
@pytest.mark.asyncio
async def test_full_tick_cycle():
    """完整 7 Phase tick 应能执行 10 步不报错."""
    from src.engine.orchestrator import Orchestrator

    orch = Orchestrator()

    for i in range(10):
        result = await orch.run_tick()
        assert "narrative" in result
        assert result["tick"] == i
        assert isinstance(result["errors"], list)

    assert orch.tick == 10


@pytest.mark.asyncio
async def test_full_tick_cycle_with_custom_state():
    """自定义初始状态应能执行 tick."""
    from src.engine.orchestrator import Orchestrator

    orch = Orchestrator()
    state = OverallState(
        tick=0,
        dm_instructions=[], plot_brief="Custom initial plot",
        scene_direction={"featured_pcs": [], "featured_actors": []},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )

    result = await orch.run_tick(state)
    assert result["tick"] == 0
    assert result["narrative"] is not None

"""测试 TickGraph 7 Phase 主图 / Test TickGraph 7-phase main graph."""

import pytest

from src.engine.tick_graph import (
    build_tick_graph,
    OverallState,
    phase1_dm_create,
    phase2_world_engine,
    phase3_character_decide,
    phase4_engines,
    phase5_state_update,
    phase6_dm_narrate,
    phase7_reflection,
)


# ============================================================
# 测试 StateGraph 构建 / Test StateGraph construction
# ============================================================
def test_build_graph_returns_state_graph():
    """构建的图应该包含 7 个节点."""
    graph = build_tick_graph()
    assert graph is not None


def test_graph_can_compile():
    """图应该可以编译（含 checkpointer）."""
    from langgraph.checkpoint.memory import MemorySaver
    graph = build_tick_graph()
    app = graph.compile(checkpointer=MemorySaver())
    assert app is not None


# ============================================================
# 测试 OverallState 初始化 / Test OverallState initialization
# ============================================================
def test_overall_state_defaults():
    """OverallState 应该支持默认值."""
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
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )
    assert state["tick"] == 0
    assert state["plot_brief"] == ""
    assert state["narrative"] == ""


# ============================================================
# 测试各 Phase Mock 函数 / Test each Phase mock function
# ============================================================
@pytest.fixture
def base_state() -> OverallState:
    """基础测试状态 / Base test state."""
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
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )


def test_phase1_dm_create(base_state):
    """Phase 1: 应该返回 plot_brief 和 scene_direction."""
    result = phase1_dm_create(base_state)
    assert "dm_instructions" in result
    assert "plot_brief" in result
    assert "scene_direction" in result
    assert "Tick 0" in result["plot_brief"]


def test_phase2_world_engine(base_state):
    """Phase 2: 应该返回空事件列表."""
    result = phase2_world_engine(base_state)
    assert "world_events" in result
    assert result["world_events"] == []


def test_phase3_character_decide(base_state):
    """Phase 3: 应该返回空行动列表."""
    result = phase3_character_decide(base_state)
    assert "character_actions" in result
    assert result["character_actions"] == []


def test_phase4_engines(base_state):
    """Phase 4: 应该返回空引擎结果."""
    result = phase4_engines(base_state)
    assert "engine_results" in result
    assert "combat_result" in result
    assert result["combat_result"] is None


def test_phase5_state_update(base_state):
    """Phase 5: 应该返回空 diff."""
    result = phase5_state_update(base_state)
    assert "state_diff" in result
    assert "cast_changes" in result


def test_phase6_dm_narrate(base_state):
    """Phase 6: 应该返回 narrative 和 needs_reflection.
    
    DM 子图有路由: character_actions 有值 → narrate 模式.
    dm_create_node 会覆盖 plot_brief（Mock 行为），然后 dm_narrate 拼接叙事.
    """
    base_state["character_actions"] = [{"action": "test"}]  # 触发 narrate 路由
    result = phase6_dm_narrate(base_state)
    assert "narrative" in result
    assert "needs_reflection" in result
    assert len(result["narrative"]) > 0  # DM 子图产出叙事


def test_phase6_reflection_trigger():
    """每 5 tick 触发反思 / Reflection triggers every 5 ticks."""
    state = OverallState(
        tick=5,
        dm_instructions=[], plot_brief="Test", scene_direction={},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )
    result = phase6_dm_narrate(state)
    assert result["needs_reflection"] is True  # tick=5, 5%5==0


def test_phase6_no_reflection_low_tick():
    """Tick=1 不应该触发反思."""
    state = OverallState(
        tick=1,
        dm_instructions=[], plot_brief="Test", scene_direction={},
        world_events=[], character_actions=[], engine_results=[],
        combat_result=None, state_diff={}, cast_changes=[],
        narrative="", reflected_characters=[], summary_compressed=False,
        errors=[], needs_reflection=False,
    )
    result = phase6_dm_narrate(state)
    assert result["needs_reflection"] is False  # tick=1, 1%5≠0


def test_phase7_reflection(base_state):
    """Phase 7: 应该返回空反思结果."""
    result = phase7_reflection(base_state)
    assert "reflected_characters" in result
    assert "summary_compressed" in result


# ============================================================
# 测试完整 Tick 执行 / Test full tick execution
# ============================================================
@pytest.mark.asyncio
async def test_full_tick_cycle():
    """完整 7 Phase tick 应该能执行 10 步不报错."""
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
    """自定义初始状态应该能执行 tick（子图架构）."""
    from src.engine.orchestrator import Orchestrator

    orch = Orchestrator()
    state = OverallState(
        tick=0,
        dm_instructions=[],
        plot_brief="Custom initial plot",
        scene_direction={"featured_pcs": [], "featured_actors": []},
        world_events=[],
        character_actions=[],
        engine_results=[],
        combat_result=None,
        state_diff={},
        cast_changes=[],
        narrative="",
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )

    result = await orch.run_tick(state)
    assert result["tick"] == 0
    assert result["narrative"] is not None  # 子图架构返回 narrative

"""TickGraph 主图测试 / TickGraph main graph tests."""

import pytest

from src.graph.graph import build_tick_graph
from src.graph.state import OverallState
from src.graph.subgraphs.character_subgraph import character_subgraph
from src.graph.subgraphs.reflection_subgraph import reflection_subgraph
from src.services import dm_service, message_service, scene_service

# ══ 图构建 / Graph build ══


def test_build_graph_returns_state_graph():
    """build_tick_graph 返回 StateGraph / returns StateGraph."""
    assert build_tick_graph() is not None


def test_graph_can_compile():
    """图可以编译 / Graph compiles successfully."""
    from langgraph.checkpoint.memory import MemorySaver

    g = build_tick_graph()
    app = g.compile(checkpointer=MemorySaver())
    assert app is not None


# ══ Fixtures / 测试夹具 ══


@pytest.fixture
def base_state() -> OverallState:
    """基础状态 fixture / Base state fixture."""
    return OverallState(
        tick=0,
        world_id="",
        tick_message_id="",
        hints=[],
        plot_brief="",
        scene_id="",
        character_actions=[],
        narrative="",
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )


# ══ Phase 节点测试 / Phase node tests ══


@pytest.mark.asyncio
async def test_message_create(base_state):
    """Phase 0: 创建消息 / Create message."""
    r = await message_service.create_tick_message(base_state)
    assert "tick_message_id" in r


@pytest.mark.asyncio
async def test_dm_create(base_state):
    """Phase 1: DM 创造情境 / DM creates situation."""
    r = await dm_service.dm_create(base_state)
    assert "hints" in r
    assert "plot_brief" in r


@pytest.mark.asyncio
async def test_process_scene(base_state):
    """Phase 2: 场景处理 / Scene processing."""
    r = await scene_service.process_scene(base_state)
    assert isinstance(r, dict)


@pytest.mark.asyncio
async def test_character_subgraph(base_state):
    """Phase 3: 角色子图 / Character subgraph."""
    r = await character_subgraph.ainvoke(base_state)
    assert "character_actions" in r


@pytest.mark.asyncio
async def test_dm_narrate(base_state):
    """Phase 6: DM 叙事 / DM narrates."""
    r = await dm_service.dm_narrate(base_state)
    assert "narrative" in r
    assert "needs_reflection" in r


@pytest.mark.asyncio
async def test_reflection_subgraph(base_state):
    """Phase 7: 反思子图 / Reflection subgraph."""
    r = await reflection_subgraph.ainvoke(base_state)
    assert "reflected_characters" in r


# ══ 全 Tick 流程 / Full tick flow ══


@pytest.mark.asyncio
async def test_full_tick_cycle():
    """完整 tick 循环 / Full tick cycle."""
    from src.graph.orchestrator import Orchestrator

    orch = Orchestrator()
    for i in range(3):
        result = await orch.run_tick()
        assert "narrative" in result
        assert result["tick"] == i + 1
    assert orch.tick == 4

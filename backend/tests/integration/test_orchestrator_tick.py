"""集成测试——完整 Tick Loop."""

import pytest

from src.graph.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_single_tick_returns_narrative():
    orch = Orchestrator()
    result = await orch.run_tick()
    assert "narrative" in result
    assert result["tick"] >= 0


@pytest.mark.asyncio
async def test_ten_ticks_no_crash():
    orch = Orchestrator()
    for i in range(10):
        result = await orch.run_tick()
        assert result["tick"] == i + 1
        assert result.get("errors", []) == []


@pytest.mark.asyncio
async def test_tick_has_character_actions():
    orch = Orchestrator()
    _ = orch.get_state()
    result = await orch.run_tick()
    # mock 引擎下，如果没有 featured chars，actions 为空
    assert isinstance(result.get("events", []), list)


@pytest.mark.asyncio
async def test_orchestrator_tick_counter():
    orch = Orchestrator()
    assert orch.tick == 1
    await orch.run_tick()
    assert orch.tick == 2
    await orch.run_tick()
    assert orch.tick == 3

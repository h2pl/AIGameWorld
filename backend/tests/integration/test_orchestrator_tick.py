"""集成测试——完整 Tick Loop."""

import pytest

from src.graph.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_single_tick_returns_narrative():
    orch = Orchestrator()
    result = await orch.run_tick("test")
    assert "narrative" in result
    assert result["tick"] >= 0


@pytest.mark.asyncio
async def test_ten_ticks_no_crash():
    orch = Orchestrator()
    for i in range(10):
        result = await orch.run_tick("test")
        assert result.get("errors", []) == []


@pytest.mark.asyncio
async def test_tick_has_pc_actions():
    orch = Orchestrator()
    result = await orch.run_tick("test")
    assert isinstance(result.get("pc_decisions", []), list)


@pytest.mark.asyncio
async def test_orchestrator_tick_counter():
    orch = Orchestrator()
    r1 = await orch.run_tick("test")
    assert r1["tick"] >= 1
    r2 = await orch.run_tick("test")
    assert r2["tick"] == r1["tick"] + 1

"""集成测试——完整 Tick Loop / Integration tests for full tick loop."""

import pytest

from src.graph.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_single_tick_returns_tick(mock_repos):
    """单个 tick 返回 tick 编号 / Single tick returns tick number."""
    # 使用 mock repos 创建编排器 / Create orchestrator with mock repos
    orch = Orchestrator(repos=mock_repos)
    result = await orch.run_tick("test")
    assert "tick" in result
    assert result["tick"] >= 0


@pytest.mark.asyncio
async def test_ten_ticks_no_crash(mock_repos):
    """连续 10 个 tick 不崩溃 / Ten consecutive ticks do not crash."""
    orch = Orchestrator(repos=mock_repos)
    for _ in range(10):
        result = await orch.run_tick("test")
        assert result.get("errors", []) == []


@pytest.mark.asyncio
async def test_tick_has_pc_actions(mock_repos):
    """tick 结果包含 pc_decisions 列表 / Tick result contains pc_decisions list."""
    orch = Orchestrator(repos=mock_repos)
    result = await orch.run_tick("test")
    assert isinstance(result.get("pc_decisions", []), list)


@pytest.mark.asyncio
async def test_orchestrator_tick_counter(mock_repos):
    """tick 计数器逐次递增 / Tick counter increments sequentially."""
    orch = Orchestrator(repos=mock_repos)
    r1 = await orch.run_tick("test")
    assert r1["tick"] >= 1
    r2 = await orch.run_tick("test")
    assert r2["tick"] == r1["tick"] + 1

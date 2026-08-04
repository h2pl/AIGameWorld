"""Orchestrator checkpoint 集成测试——验证 session 隔离."""

import pytest

from src.domain.world import World
from src.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_session_isolation(mock_repos):
    """不同 world_id 的状态互不影响."""
    # 测试内创建额外的 world / Create additional worlds within the test
    await mock_repos["world"].create(World(id="world-a", name="World A"))
    await mock_repos["world"].create(World(id="world-b", name="World B"))

    orch = Orchestrator(repos=mock_repos, llm=mock_repos["llm"])

    result_a = await orch.run_tick("world-a")
    result_b = await orch.run_tick("world-b")

    assert result_a["tick"] == 1
    assert result_b["tick"] == 1

    result_a2 = await orch.run_tick("world-a")
    assert result_a2["tick"] == 2


@pytest.mark.asyncio
async def test_tick_returns_result(mock_repos):
    """每次 tick 后返回有效结果."""
    orch = Orchestrator(repos=mock_repos, llm=mock_repos["llm"])

    result = await orch.run_tick("test")
    assert "tick" in result
    assert result["tick"] >= 1

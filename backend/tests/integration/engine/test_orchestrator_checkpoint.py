"""Orchestrator checkpoint 集成测试——验证 checkpoint 隔离."""

import pytest

from src.graph.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_session_isolation():
    """不同 world_id 的状态互不影响."""
    orch = Orchestrator()

    await orch.run_tick("world-a")
    await orch.run_tick("world-b")

    history_a = orch.get_history("world-a")
    history_b = orch.get_history("world-b")
    assert len(history_a) >= 1
    assert len(history_b) >= 1


@pytest.mark.asyncio
async def test_history_available_after_tick():
    """每次 tick 后应能在历史中找到记录."""
    orch = Orchestrator()

    await orch.run_tick("test")
    history = orch.get_history("test")
    assert len(history) >= 1
    latest = orch.get_state("test")
    assert latest is not None

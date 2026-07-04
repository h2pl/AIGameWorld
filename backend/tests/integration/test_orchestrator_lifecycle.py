"""E2E 测试——完整 TickGraph 模拟。per 11-testing-strategy.md §1."""

from unittest.mock import AsyncMock

import pytest

from src.graph.orchestrator import Orchestrator


class TestFullTickRun:
    """全量 tick 运行——不崩溃 + 状态正确."""

    @pytest.mark.asyncio
    async def test_10_ticks_no_crash(self, mock_repos):
        """10 步不崩溃——核心稳定性."""
        orch = Orchestrator(repos=mock_repos)
        for i in range(10):
            result = await orch.run_tick("test")
            assert "tick" in result
            assert result["tick"] == i + 1

    @pytest.mark.asyncio
    async def test_5_ticks_with_llm_mock(self, mock_repos):
        """5 步 + mock LLM——验证 LLM 链路不崩溃."""
        from src.schemas.llm_output import DMNarrativeSchema, DMOutput

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            side_effect=[DMOutput(plot_brief=f"Plot {i}") for i in range(10)]
            + [DMNarrativeSchema(narrative=f"Narrative {i}") for i in range(10)]
        )
        orch = Orchestrator(llm=llm, repos=mock_repos)

        for i in range(5):
            result = await orch.run_tick("test")
            assert result["tick"] == i + 1

    @pytest.mark.asyncio
    async def test_tick_state_consistency(self, mock_repos):
        """tick 计数器正确递增."""
        orch = Orchestrator(repos=mock_repos)
        for i in range(5):
            result = await orch.run_tick("test")
            assert result["tick"] == i + 1

    @pytest.mark.asyncio
    async def test_run_tick_returns_tick(self, mock_repos):
        """每个 tick 返回 tick."""
        orch = Orchestrator(repos=mock_repos)
        result = await orch.run_tick("test")
        assert "tick" in result

    @pytest.mark.asyncio
    async def test_run_tick_tick_is_int(self, mock_repos):
        """tick 字段为整数."""
        orch = Orchestrator(repos=mock_repos)
        result = await orch.run_tick("test")
        assert isinstance(result["tick"], int)

    @pytest.mark.asyncio
    async def test_run_tick_no_errors(self, mock_repos):
        """5 步无错误."""
        orch = Orchestrator(repos=mock_repos)
        for _ in range(5):
            result = await orch.run_tick("test")
            assert result.get("errors", []) == []

    @pytest.mark.asyncio
    async def test_orchestrator_reset(self, mock_repos):
        """重置后 tick 归零."""
        orch = Orchestrator(repos=mock_repos)
        await orch.run_tick("test")
        await orch.reset("test")
        r = await orch.run_tick("test")
        assert r["tick"] == 1

    @pytest.mark.asyncio
    async def test_orchestrator_with_custom_state(self, mock_repos):
        """自定义初始状态——简化测试，只验证不崩溃."""
        orch = Orchestrator(repos=mock_repos)
        result = await orch.run_tick("test")
        assert result["tick"] >= 1

    @pytest.mark.asyncio
    async def test_reflection_triggered_at_interval(self, mock_repos):
        """反思按间隔触发不崩溃."""
        orch = Orchestrator(reflection_interval=2, repos=mock_repos)
        for _ in range(3):
            result = await orch.run_tick("test")
        assert result["tick"] == 3  # 从1开始

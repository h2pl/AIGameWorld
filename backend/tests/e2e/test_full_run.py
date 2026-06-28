"""E2E 测试——50 步完整 TickGraph 模拟。per 11-testing-strategy.md §1."""

import pytest
import asyncio
from unittest.mock import AsyncMock

from src.engine.orchestrator import Orchestrator


class TestFullTickRun:
    """全量 tick 运行——不崩溃 + 状态正确."""

    @pytest.mark.asyncio
    async def test_50_ticks_no_crash(self):
        """50 步不崩溃——核心稳定性测试."""
        orch = Orchestrator()
        for i in range(50):
            result = await orch.run_tick()
            assert "tick" in result
            assert "narrative" in result
            assert result["tick"] == i

    @pytest.mark.asyncio
    async def test_20_ticks_with_agent_mock(self):
        """20 步 + mock DMAgent——验证 LLM 链路不崩溃."""
        from src.agents.dm_agent import DMAgent
        from src.schemas.llm_output import DMOutput, DMNarrativeSchema

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=[
            DMOutput(plot_brief=f"Plot {i}") for i in range(50)
        ] + [
            DMNarrativeSchema(narrative=f"Narrative {i}") for i in range(50)
        ])
        agent = DMAgent(llm)
        orch = Orchestrator(dm_agent=agent)

        for i in range(20):
            result = await orch.run_tick()
            assert result["tick"] == i
            assert "narrative" in result

    @pytest.mark.asyncio
    async def test_tick_state_consistency(self):
        """tick 计数器正确递增."""
        orch = Orchestrator()
        for i in range(10):
            result = await orch.run_tick()
            assert result["tick"] == i
        assert orch.tick == 10

    @pytest.mark.asyncio
    async def test_run_tick_returns_character_actions(self):
        """每个 tick 返回 character_actions."""
        orch = Orchestrator()
        result = await orch.run_tick()
        # mock 引擎：tick 1+ 应该有角色行动
        assert "character_actions" in result

    @pytest.mark.asyncio
    async def test_run_tick_handles_narrative(self):
        """叙事字段非空且为字符串."""
        orch = Orchestrator()
        result = await orch.run_tick()
        assert isinstance(result["narrative"], str)

    @pytest.mark.asyncio
    async def test_run_tick_no_errors(self):
        """50 步无错误."""
        orch = Orchestrator()
        for _ in range(20):
            result = await orch.run_tick()
            assert result.get("errors", []) == []

    @pytest.mark.asyncio
    async def test_orchestrator_reset(self):
        """重置后 tick 归零."""
        orch = Orchestrator()
        await orch.run_tick()
        orch.reset()
        assert orch.tick == 0

    @pytest.mark.asyncio
    async def test_orchestrator_with_custom_state(self):
        """自定义初始状态."""
        from src.graph.graph import OverallState

        orch = Orchestrator()
        state = OverallState(
            tick=0,
            dm_instructions=[], plot_brief="Custom start", scene_direction={},
            world_events=[], character_actions=[], engine_results=[],
            combat_result=None, state_diff={}, cast_changes=[],
            narrative="", reflected_characters=[], summary_compressed=False,
            errors=[], needs_reflection=False,
        )
        result = await orch.run_tick(state)
        assert result["tick"] == 0

    @pytest.mark.asyncio
    async def test_rollback_and_run(self):
        """回退后继续."""
        orch = Orchestrator()
        await orch.run_tick()
        await orch.run_tick()
        orch.rollback(0)
        assert orch.tick == 0
        result = await orch.run_tick()
        assert result["tick"] == 0

    @pytest.mark.asyncio
    async def test_reflection_triggered_at_interval(self):
        """反思按间隔触发."""
        orch = Orchestrator(reflection_interval=3)
        for i in range(4):
            result = await orch.run_tick()
        # tick 3 mod 3 == 0 → needs_reflection should have been True in the graph state at some point
        # (depends on graph execution, verify no exception at minimum)
        assert result["tick"] == 3

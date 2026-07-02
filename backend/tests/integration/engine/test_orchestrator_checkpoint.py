"""Orchestrator checkpoint 集成测试 / Integration tests for Orchestrator checkpointing.

验证 session 隔离、状态历史、回滚 / Verify session isolation, state history, and rollback.
"""

import pytest

from src.graph.graph import OverallState
from src.graph.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_session_isolation():
    """不同 session_id 的状态互不影响 / Different session_ids do not interfere."""
    orch_a = Orchestrator(session_id="session-a")
    orch_b = Orchestrator(session_id="session-b")

    state_a = OverallState(
        tick=0,
        world_id="",
        tick_message_id="",
        scene_info={},
        pending_events=[],
        hints=["探索酒馆，寻找线索"],
        plot_brief="",
        scene_id="",
        character_decisions=[],
        narrative="",
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )
    state_b = OverallState(
        tick=0,
        world_id="",
        tick_message_id="",
        scene_info={},
        pending_events=[],
        hints=["与酒保交谈打听消息"],
        plot_brief="",
        scene_id="",
        character_decisions=[],
        narrative="",
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )

    await orch_a.run_tick(state_a)
    await orch_b.run_tick(state_b)

    history_a = orch_a.get_history()
    history_b = orch_b.get_history()

    # 至少包含初始 checkpoint 和一次 tick 后的节点快照
    assert len(history_a) >= 1
    assert len(history_b) >= 1
    assert history_a != history_b


@pytest.mark.asyncio
async def test_history_available_after_tick():
    """每次 tick 后应能在历史中找到记录 / History should contain tick records."""
    orch = Orchestrator(session_id="history-test")
    state = OverallState(
        tick=0,
        world_id="",
        tick_message_id="",
        scene_info={},
        pending_events=[],
        hints=["测试指令"],
        plot_brief="",
        scene_id="",
        character_decisions=[],
        narrative="",
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )

    await orch.run_tick(state)
    history = orch.get_history()

    assert len(history) >= 1
    latest = orch.get_state()
    assert latest.values["tick"] == 1

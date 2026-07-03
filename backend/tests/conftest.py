"""共享 fixtures——per 11-testing-strategy.md §3."""

import pytest

from src.graph.state import OverallState


@pytest.fixture
def base_state() -> OverallState:
    """基础 mock state."""
    return OverallState(
        tick=0,
        world_id="",
        tick_message_id="",
        scene_info={},
        pending_actions=[],
        hints=[],
        plot_brief="",
        scene_id="",
        pc_decisions=[],
        narrative="",
    )

"""共享 fixtures——per 11-testing-strategy.md §3."""

import pytest

from src.graph.graph import OverallState


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
        character_decisions=[],
        narrative="",
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )

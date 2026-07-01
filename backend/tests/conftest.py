"""共享 fixtures——per 11-testing-strategy.md §3."""

import pytest

from src.graph.graph import OverallState


@pytest.fixture
def base_state() -> OverallState:
    """基础 mock state."""
    return OverallState(
        tick=0,
        world_id="",
        dm_instructions=[],
        plot_brief="",
        scene={},
        scene_events=[],
        character_actions=[],
        engine_results=[],
        combat_result=None,
        state_diff={},
        narrative="",
        branch_points=[],
        hooks_resolved=[],
        reflected_characters=[],
        summary_compressed=False,
        errors=[],
        needs_reflection=False,
    )

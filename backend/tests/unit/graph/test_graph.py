"""TickGraph 主图测试——对齐当前主图结构。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from src.graph.graph import build_tick_graph
from src.schemas.response import SceneObservation


def _graph_input(**overrides):
    """构造主图输入 / Build graph input."""
    return {
        "tick": 5,
        "world_id": "world-1",
        "tick_message_id": "",
        "scene_observations": [],
        "hints": [],
        "plot_brief": "",
        "scene_id": "scene-1",
        "character_actions": [],
        "narrative": "",
        "reflected_characters": [],
        "summary_compressed": False,
        "errors": [],
        "needs_reflection": False,
        **overrides,
    }


def test_build_graph_returns_state_graph():
    """主图可构建 / Main graph can be built."""
    assert build_tick_graph() is not None


def test_graph_can_compile():
    """主图可编译 / Main graph can compile."""
    app = build_tick_graph().compile(checkpointer=MemorySaver())
    assert app is not None


@pytest.mark.asyncio
async def test_full_tick_graph_runs_current_flow():
    """主图按当前顺序执行 / Main graph runs current flow."""
    app = build_tick_graph().compile(checkpointer=MemorySaver())
    dm_create_result = AsyncMock(
        return_value=type(
            "DMCreateResult",
            (),
            {"hints": ["去吧台"], "plot_brief": "酒馆有事", "scene_id": "tavern", "errors": []},
        )()
    )
    dm_narrate_result = AsyncMock(
        return_value=type(
            "DMNarrateResult",
            (),
            {"narrative_out": "夜幕降临。", "errors": []},
        )()
    )
    # 场景内唯一一个 PC / The only PC in the scene
    pc = SimpleNamespace(id="pc-1", scene_id="tavern")
    char_repo = AsyncMock()
    char_repo.load_pcs = AsyncMock(return_value=[pc])
    observation = SceneObservation(pc_id="pc-1")

    with (
        patch(
            "src.services.message_service.message_engine.create_tick_message",
            AsyncMock(return_value="tick-1"),
        ),
        patch(
            "src.services.dm_service.dm_engine.dm_create",
            dm_create_result,
        ),
        patch(
            "src.services.scene_service.scene_engine.process_scene_setup",
            AsyncMock(),
        ),
        patch(
            "src.services.scene_service.scene_engine.process_scene_objects",
            AsyncMock(),
        ),
        patch(
            "src.services.character_service.observation_engine.observe_scene",
            AsyncMock(return_value=observation),
        ),
        patch(
            "src.services.character_service.decision_engine.decide",
            AsyncMock(return_value={"pc_id": "pc-1", "type": "wait", "description": "观察"}),
        ),
        patch(
            "src.services.character_service.talk_engine.process_talk_action",
            AsyncMock(),
        ),
        patch(
            "src.services.character_service.exploration_engine.process_explore_action",
            AsyncMock(),
        ),
        patch(
            "src.services.dm_service.dm_engine.dm_narrate",
            dm_narrate_result,
        ),
        patch(
            "src.services.reflection_service.get_repo",
            side_effect=[None, None],
        ),
    ):
        result = await app.ainvoke(
            _graph_input(),
            config={
                "configurable": {
                    "thread_id": "test-thread",
                    "reflection_interval": 5,
                    "repos": {"char": char_repo},
                }
            },
        )
    assert result["tick_message_id"] == "tick-1"
    assert result["scene_id"] == "tavern"
    assert result["narrative"] == "夜幕降临。"
    assert result["reflected_characters"] == []

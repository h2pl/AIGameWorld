"""TickGraph 主图测试——对齐当前主图结构。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from src.graph.graph import build_tick_graph


def _graph_input(**overrides):
    """构造主图输入 / Build graph input."""
    return {
        "tick": 5,
        "world_id": "world-1",
        "tick_message_id": "",
        "scene_info": {},
        "pending_actions": [],
        "hints": [],
        "plot_brief": "",
        "scene_id": "scene-1",
        "character_decisions": [],
        "narrative": "",
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
            {"hints": ["去吧台"], "plot_brief": "酒馆有事", "scene_id": "tavern"},
        )()
    )
    dm_narrate_result = AsyncMock(
        return_value=type(
            "DMNarrateResult",
            (),
            {"narrative_out": "夜幕降临。"},
        )()
    )
    # 场景内唯一一个 PC / The only PC in the scene
    pc = SimpleNamespace(
        id="pc-1", scene_id="tavern", name="Alex", role="fighter", race="human", status="active"
    )
    char_repo = AsyncMock()
    char_repo.load_pcs = AsyncMock(return_value=[pc])
    char_repo.load_actors = AsyncMock(return_value=[])
    scene_repo = AsyncMock()
    scene_repo.get_scene = AsyncMock(return_value=None)
    scene_repo.get_object_ids = AsyncMock(return_value=[])
    scene_repo.load_all = AsyncMock(return_value={})
    message_repo = AsyncMock()

    with (
        patch(
            "src.services.dm_service.dm_engine.dm_create",
            dm_create_result,
        ),
        patch(
            "src.services.character_service.decision_engine.decide",
            AsyncMock(return_value={"pc_id": "pc-1", "type": "wait", "description": "观察"}),
        ),
        patch(
            "src.services.character_service.talk_engine.process_talk_action",
            AsyncMock(return_value=None),
        ),
        patch(
            "src.services.character_service.interact_engine.process_interact_action",
            AsyncMock(return_value=None),
        ),
        patch(
            "src.services.character_service.combat_engine.process_combat_action",
            AsyncMock(return_value=None),
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
                    "repos": {"char": char_repo, "scene": scene_repo, "message": message_repo},
                }
            },
        )
    assert result["tick_message_id"] == "tick_5"
    assert result["scene_id"] == "tavern"
    assert result["narrative"] == "夜幕降临。"

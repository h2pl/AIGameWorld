"""Explore Engine 单元测试 / Unit tests for explore engine."""

from unittest.mock import AsyncMock

import pytest

from src.domain import Decision
from src.domain.player_character import PlayerCharacter
from src.domain.scene import Scene
from src.engine.explore.explore_engine import process_explore_action
from src.schemas.llm_output import ExploreOutputSchema


def _mock_config(llm=None):
    """构造带 repo mock 的 config / Build config with repo mocks."""
    memory_repo = AsyncMock()
    memory_repo.retrieve = AsyncMock(return_value=[])
    memory_repo.store = AsyncMock(return_value=None)
    memory_repo.retrieve_reflections = AsyncMock(return_value=[])
    memory_repo.get_recent = AsyncMock(return_value=[])  # async method
    memory_repo.search_long_term_vector = lambda *a, **kw: []  # sync method
    memory_repo.fetch_long_term_sqlite = AsyncMock(return_value=[])
    cfg = {"configurable": {"repos": {"memory": memory_repo}}}
    if llm:
        cfg["configurable"]["llm"] = llm
    return cfg


def _pc(position_x: int = 0, position_y: int = 0) -> PlayerCharacter:
    return PlayerCharacter(
        id="pc1",
        name="pc1",
        role="adventurer",
        personality="",
        position_x=position_x,
        position_y=position_y,
    )


class TestExploreEngine:
    @pytest.mark.asyncio
    async def test_non_explore_action_skipped(self):
        """非 explore 类型被跳过 / Non-explore action is skipped."""
        event = await process_explore_action(
            decision=Decision(type="talk", pc_id="pc1"),
            tick=1,
            scene=Scene(id="test"),
            pcs={},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_llm_destination_clamped(self):
        """LLM 返回的终点坐标被裁剪到地图范围内 / LLM destination clamped to map bounds."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=ExploreOutputSchema(
                end_x=999,
                end_y=-5,
                explore_record="发现一枚古币。",
            )
        )
        config = _mock_config(llm=llm)
        pc = _pc(position_x=5, position_y=5)
        event = await process_explore_action(
            decision=Decision(type="explore", pc_id="pc1"),
            tick=1,
            scene=Scene(id="test", map_width=40, map_height=40),
            pcs={"pc1": pc},
            config=config,
        )
        assert event is not None
        assert event.action_type == "explore"
        assert event.pc_id == "pc1"
        assert event.explore_record == "发现一枚古币。"
        assert len(event.waypoints) == 2
        assert event.waypoints[0] == {"x": 5, "y": 5}
        assert event.waypoints[1] == {"x": 39, "y": 0}
        assert pc.position_x == 39
        assert pc.position_y == 0

    @pytest.mark.asyncio
    async def test_same_position_returns_none(self):
        """LLM 返回终点=起点时返回 None / Returns None when destination = start."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=ExploreOutputSchema(
                end_x=5,
                end_y=5,
                explore_record="原地不动。",
            )
        )
        config = _mock_config(llm=llm)
        event = await process_explore_action(
            decision=Decision(type="explore", pc_id="pc1"),
            tick=1,
            scene=Scene(id="test", map_width=40, map_height=40),
            pcs={"pc1": _pc(position_x=5, position_y=5)},
            config=config,
        )
        assert event is None

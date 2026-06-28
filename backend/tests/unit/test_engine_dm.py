"""engine/dm/dm.py 单元测试——mock + agent 双路径."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.schemas.request import DMCreateRequest, DMNarrateRequest


class TestDMCreate:
    """dm_create——mock 和 agent 路径."""

    @pytest.mark.asyncio
    async def test_mock_path(self):
        from src.engine.dm import dm as dm_engine

        req = DMCreateRequest(tick=0, plot_brief="")
        result = await dm_engine.dm_create(req, agent=None)

        assert result.plot_brief != ""
        assert result.scene_direction["featured_pcs"] == ["alex", "maya"]

    @pytest.mark.asyncio
    async def test_agent_path(self):
        from src.engine.dm import dm as dm_engine

        agent = MagicMock()
        agent.create_situation = AsyncMock(return_value={
            "plot_brief": "LLM plot",
            "scene_direction": {"featured_pcs": ["garret"], "featured_actors": []},
            "instructions_out": [{"type": "test"}],
        })
        req = DMCreateRequest(tick=1, plot_brief="")
        result = await dm_engine.dm_create(req, agent=agent)

        assert result.plot_brief == "LLM plot"
        assert "garret" in result.scene_direction["featured_pcs"]
        agent.create_situation.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_ticks_different_plots(self):
        """mock 路径不同 tick 产出不同 plot."""
        from src.engine.dm import dm as dm_engine

        r0 = await dm_engine.dm_create(DMCreateRequest(tick=0, plot_brief=""))
        r1 = await dm_engine.dm_create(DMCreateRequest(tick=1, plot_brief=""))

        assert r0.plot_brief != r1.plot_brief


class TestDMNarrate:
    """dm_narrate——mock 和 agent 路径."""

    @pytest.mark.asyncio
    async def test_mock_path(self):
        from src.engine.dm import dm as dm_engine

        req = DMNarrateRequest(tick=0, plot_brief="Test plot", dm_instructions=[],
                               scene_direction={}, character_actions=[])
        result = await dm_engine.dm_narrate(req, agent=None)

        assert "Test plot" in result.narrative_out

    @pytest.mark.asyncio
    async def test_mock_with_actions(self):
        from src.engine.dm import dm as dm_engine

        req = DMNarrateRequest(
            tick=0, plot_brief="Fight!",
            dm_instructions=[], scene_direction={},
            character_actions=[{"character_id": "alex", "type": "attack"}],
        )
        result = await dm_engine.dm_narrate(req, agent=None)

        assert "Characters take 1 action" in result.narrative_out

    @pytest.mark.asyncio
    async def test_agent_path(self):
        from src.engine.dm import dm as dm_engine

        agent = MagicMock()
        agent.narrate = AsyncMock(return_value={"narrative": "LLM narrative text"})
        req = DMNarrateRequest(
            tick=0, plot_brief="Story", dm_instructions=[],
            scene_direction={}, character_actions=[],
        )
        result = await dm_engine.dm_narrate(req, agent=agent)

        assert result.narrative_out == "LLM narrative text"
        agent.narrate.assert_called_once()

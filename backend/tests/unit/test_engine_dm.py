"""DM Engine 集成测试——dm_create/narrate + LLMClient."""
import pytest
from unittest.mock import AsyncMock

from src.schemas.request import DMCreateRequest, DMNarrateRequest
from src.schemas.llm_output import DMOutput, DMNarrativeSchema, SceneDirectionOutput


class TestDMCreate:
    @pytest.mark.asyncio
    async def test_creates_situation_with_llm(self):
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(return_value=DMOutput(
            plot_brief="LLM plot",
            scene_direction=SceneDirectionOutput(featured_pcs=["garret"], featured_actors=[]),
            instructions=[{"type": "test"}],
        ))
        result = await dm_engine.dm_create(DMCreateRequest(tick=1, plot_brief=""), llm)
        assert result.plot_brief == "LLM plot"
        assert "garret" in result.scene_direction["featured_pcs"]

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=Exception("LLM down"))
        result = await dm_engine.dm_create(DMCreateRequest(tick=0, plot_brief=""), llm)
        assert "平静" in result.plot_brief


class TestDMNarrate:
    @pytest.mark.asyncio
    async def test_narrates_with_llm(self):
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(return_value=DMNarrativeSchema(
            narrative="LLM narrative text",
        ))
        req = DMNarrateRequest(tick=0, plot_brief="Story", dm_instructions=[],
                               scene_direction={}, character_actions=[])
        result = await dm_engine.dm_narrate(req, llm)
        assert result.narrative_out == "LLM narrative text"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=Exception("LLM down"))
        req = DMNarrateRequest(tick=0, plot_brief="Test", dm_instructions=[],
                               scene_direction={}, character_actions=[])
        result = await dm_engine.dm_narrate(req, llm)
        assert "DM" in result.narrative_out

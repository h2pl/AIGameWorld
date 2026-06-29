"""DM Engine 集成测试——dm_create/narrate + LLMClient + P2-4/P2-6."""

from unittest.mock import AsyncMock

import pytest

from src.schemas.llm_output import DMNarrativeSchema, DMOutput, SceneDirectionOutput
from src.schemas.request import DMCreateRequest, DMNarrateRequest


class TestDMCreate:
    @pytest.mark.asyncio
    async def test_creates_situation_with_llm(self):
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=DMOutput(
                plot_brief="LLM plot",
                scene_direction=SceneDirectionOutput(featured_pcs=["garret"], featured_actors=[]),
                instructions=["测试指令"],
            )
        )
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

    @pytest.mark.asyncio
    async def test_engine_loads_story_arcs_from_repo(self):
        """P2-4: dm_create 从 story_repo 加载 arcs/hooks（Service→Engine→Repository）."""
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=DMOutput(
                plot_brief="arc-aware plot",
                scene_direction=SceneDirectionOutput(),
                instructions=["行动"],
            )
        )
        story_repo = AsyncMock()
        story_repo.load_arcs = AsyncMock(return_value=[])
        story_repo.load_hooks = AsyncMock(return_value=[])
        result = await dm_engine.dm_create(
            DMCreateRequest(tick=2, plot_brief="prev"),
            llm,
            story_repo=story_repo,
        )
        assert result.plot_brief == "arc-aware plot"
        story_repo.load_arcs.assert_called_once()
        story_repo.load_hooks.assert_called_once()
        llm.call_structured.assert_called_once()


class TestDMNarrate:
    @pytest.mark.asyncio
    async def test_narrates_with_llm(self):
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=DMNarrativeSchema(
                narrative="LLM narrative text",
            )
        )
        req = DMNarrateRequest(
            tick=0, plot_brief="Story", dm_instructions=[], scene_direction={}, character_actions=[]
        )
        result = await dm_engine.dm_narrate(req, llm)
        assert result.narrative_out == "LLM narrative text"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=Exception("LLM down"))
        req = DMNarrateRequest(
            tick=0, plot_brief="Test", dm_instructions=[], scene_direction={}, character_actions=[]
        )
        result = await dm_engine.dm_narrate(req, llm)
        assert "DM" in result.narrative_out


class TestDMGuardrails:
    """P2-6: 业务规则护栏测试 / Business rule guardrail tests."""

    def test_validate_dm_output_fixes_invalid_mood(self):
        from src.engine.dm.dm import _validate_dm_output

        result = DMOutput(
            plot_brief="x",
            scene_direction=SceneDirectionOutput(mood="invalid_mood"),
            instructions=["a"],
        )
        fixed = _validate_dm_output(result)
        assert fixed.scene_direction.mood == "neutral"

    def test_validate_dm_output_keeps_valid_mood(self):
        from src.engine.dm.dm import _validate_dm_output

        result = DMOutput(
            plot_brief="x",
            scene_direction=SceneDirectionOutput(mood="tense"),
            instructions=["a"],
        )
        fixed = _validate_dm_output(result)
        assert fixed.scene_direction.mood == "tense"

    def test_validate_dm_output_fills_empty_instructions(self):
        from src.engine.dm.dm import _validate_dm_output

        result = DMOutput(
            plot_brief="x",
            scene_direction=SceneDirectionOutput(),
            instructions=[],
        )
        fixed = _validate_dm_output(result)
        assert len(fixed.instructions) == 1
        assert fixed.instructions[0] == "观察周围环境"

    def test_validate_dm_output_truncates_excess_instructions(self):
        from src.engine.dm.dm import _validate_dm_output

        result = DMOutput(
            plot_brief="x",
            scene_direction=SceneDirectionOutput(),
            instructions=["a", "b", "c", "d", "e", "f"],
        )
        fixed = _validate_dm_output(result)
        assert len(fixed.instructions) == 4

    def test_validate_narrate_output_fills_empty(self):
        from src.engine.dm.dm import _validate_narrate_output

        result = DMNarrativeSchema(narrative="")
        fixed = _validate_narrate_output(result)
        assert "沉默" in fixed.narrative

    def test_validate_narrate_output_fills_whitespace(self):
        from src.engine.dm.dm import _validate_narrate_output

        result = DMNarrativeSchema(narrative="   \n  ")
        fixed = _validate_narrate_output(result)
        assert "沉默" in fixed.narrative

    def test_validate_narrate_output_keeps_valid(self):
        from src.engine.dm.dm import _validate_narrate_output

        result = DMNarrativeSchema(narrative="雾气弥漫，远处传来钟声。")
        fixed = _validate_narrate_output(result)
        assert fixed.narrative == "雾气弥漫，远处传来钟声。"

"""DM Engine 集成测试——dm_create/narrate + LLMClient + P2-4/P2-6."""
import pytest
from unittest.mock import AsyncMock

from src.schemas.request import DMCreateRequest, DMNarrateRequest
from src.schemas.llm_output import DMOutput, DMNarrativeSchema, SceneDirectionOutput, BranchPoint


class TestDMCreate:
    @pytest.mark.asyncio
    async def test_creates_situation_with_llm(self):
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(return_value=DMOutput(
            plot_brief="LLM plot",
            scene_direction=SceneDirectionOutput(featured_pcs=["garret"], featured_actors=[]),
            instructions=["测试指令"],
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

    @pytest.mark.asyncio
    async def test_passes_story_arcs_and_hooks(self):
        """P2-4: story_arcs/active_hooks 参数被接收并传入模板渲染."""
        from src.engine.dm import dm as dm_engine

        llm = AsyncMock()
        llm.call_structured = AsyncMock(return_value=DMOutput(
            plot_brief="arc-aware plot",
            scene_direction=SceneDirectionOutput(),
            instructions=["行动"],
        ))
        arcs = [{"id": "arc1", "title": "主线", "stage": "铺陈"}]
        hooks = [{"id": "h1", "description": "神秘信物"}]
        result = await dm_engine.dm_create(
            DMCreateRequest(tick=2, plot_brief="prev"),
            llm,
            story_arcs=arcs,
            active_hooks=hooks,
        )
        assert result.plot_brief == "arc-aware plot"
        # 验证 call_structured 被调用（模板渲染成功即说明参数被接收）
        llm.call_structured.assert_called_once()


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

"""DM Engine LLM 测试——mock LLMClient."""

from unittest.mock import AsyncMock

import pytest

from src.schemas.llm_output import DMNarrativeSchema, DMOutput, SceneDirectionOutput


class TestDMCreate:
    @pytest.mark.asyncio
    async def test_llm_returns_valid_output(self):
        from src.engine.dm.dm import dm_create
        from src.schemas.request import DMCreateRequest

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=DMOutput(
                plot_brief="A dragon appears.",
                scene_direction=SceneDirectionOutput(
                    featured_pcs=["alex"], featured_actors=["dragon"]
                ),
            )
        )
        result = await dm_create(DMCreateRequest(tick=0, plot_brief=""), llm)
        assert result.plot_brief == "A dragon appears."
        assert "alex" in result.scene_direction["featured_pcs"]

    @pytest.mark.asyncio
    async def test_llm_fails_fallback(self):
        from src.engine.dm.dm import dm_create
        from src.schemas.request import DMCreateRequest

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=RuntimeError("boom"))
        result = await dm_create(DMCreateRequest(tick=0, plot_brief=""), llm)
        assert "平静" in result.plot_brief
        assert result.instructions_out == []


class TestDMNarrate:
    @pytest.mark.asyncio
    async def test_llm_returns_valid_narrative(self):
        from src.engine.dm.dm import dm_narrate
        from src.schemas.request import DMNarrateRequest

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=DMNarrativeSchema(
                narrative="The party fights bravely.",
            )
        )
        req = DMNarrateRequest(
            tick=0,
            plot_brief="Fight!",
            dm_instructions=[],
            scene_direction={},
            character_actions=[],
        )
        result = await dm_narrate(req, llm)
        assert result.narrative_out == "The party fights bravely."

    @pytest.mark.asyncio
    async def test_llm_fails_fallback(self):
        from src.engine.dm.dm import dm_narrate
        from src.schemas.request import DMNarrateRequest

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=RuntimeError("boom"))
        req = DMNarrateRequest(
            tick=0, plot_brief="Test", dm_instructions=[], scene_direction={}, character_actions=[]
        )
        result = await dm_narrate(req, llm)
        assert "DM" in result.narrative_out


class TestDMSafety:
    """System Prompt 铁律."""

    def test_system_prompt_loaded(self):
        from src.engine.dm.dm import _DM_SYSTEM_PROMPT

        assert "Dungeon Master" in _DM_SYSTEM_PROMPT
        assert "不扮演任何角色" in _DM_SYSTEM_PROMPT

    def test_system_prompt_no_dialogue(self):
        from src.engine.dm.dm import _DM_SYSTEM_PROMPT

        assert "不写角色的对话内容" in _DM_SYSTEM_PROMPT
        assert "不替任何角色做决策" in _DM_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_fallback_plot_has_no_dialogue_markers(self):
        from src.engine.dm.dm import dm_create
        from src.schemas.request import DMCreateRequest

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=RuntimeError("boom"))
        result = await dm_create(DMCreateRequest(tick=0, plot_brief=""), llm)
        plot = result.plot_brief
        assert '："' not in plot
        assert ':"' not in plot

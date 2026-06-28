"""agents/ 单元测试——LLMClient + DMAgent mock."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.schemas.llm_output import DMOutput, DMNarrativeSchema, SceneDirectionOutput


class TestDMAgent:
    """DMAgent create_situation + narrate 测试（mock LLM）."""

    @pytest.mark.asyncio
    async def test_create_situation_mock(self):
        from src.agents.dm_agent import DMAgent

        agent = DMAgent(AsyncMock())
        result = await agent.create_situation(plot_brief_prev="Prev plot.")

        assert "plot_brief" in result
        assert "scene_direction" in result
        assert "instructions_out" in result

    @pytest.mark.asyncio
    async def test_create_situation_with_llm(self):
        from src.agents.dm_agent import DMAgent, _DM_SYSTEM_PROMPT

        llm = MagicMock()
        expected = DMOutput(
            plot_brief="A dragon appears.",
            scene_direction=SceneDirectionOutput(
                featured_pcs=["alex"],
                featured_actors=["dragon"],
            ),
        )
        llm.call_structured = AsyncMock(return_value=expected)
        agent = DMAgent(llm)

        result = await agent.create_situation(plot_brief_prev="Camping.")

        assert result["plot_brief"] == "A dragon appears."
        assert "alex" in result["scene_direction"]["featured_pcs"]
        assert "dragon" in result["scene_direction"]["featured_actors"]
        llm.call_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_situation_llm_fails_fallback(self):
        from src.agents.dm_agent import DMAgent

        llm = MagicMock()
        llm.call_structured = AsyncMock(return_value=None)
        agent = DMAgent(llm)

        result = await agent.create_situation(plot_brief_prev="Test")

        assert "平静" in result["plot_brief"]
        assert result["instructions_out"] == []

    @pytest.mark.asyncio
    async def test_narrate_mock(self):
        from src.agents.dm_agent import DMAgent

        agent = DMAgent(AsyncMock())
        result = await agent.narrate(plot_brief="Test", character_actions=[])

        assert "narrative" in result
        assert "branch_points" in result
        assert "hooks_resolved" in result

    @pytest.mark.asyncio
    async def test_narrate_with_llm(self):
        from src.agents.dm_agent import DMAgent

        llm = MagicMock()
        expected = DMNarrativeSchema(narrative="The party fights bravely.")
        llm.call_structured = AsyncMock(return_value=expected)
        agent = DMAgent(llm)

        result = await agent.narrate(
            plot_brief="A fight breaks out.",
            character_actions=[{"character_id": "alex", "type": "combat"}],
        )

        assert result["narrative"] == "The party fights bravely."
        llm.call_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_prompt_loaded(self):
        """§5.4 System Prompt 不为空."""
        from src.agents.dm_agent import _DM_SYSTEM_PROMPT

        assert "Dungeon Master" in _DM_SYSTEM_PROMPT
        assert "不扮演任何角色" in _DM_SYSTEM_PROMPT

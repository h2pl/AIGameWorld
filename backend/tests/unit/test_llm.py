"""agents/ 单元测试——LLMClient + DMAgent mock."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.schemas.llm_output import DMOutput, DMNarrativeSchema, SceneDirectionOutput


class TestDMAgent:
    """DMAgent create_situation + narrate 测试（mock LLM）."""

    @pytest.mark.asyncio
    async def test_create_situation_mock(self):
        from src.llm.dm_agent import DMAgent

        agent = DMAgent(AsyncMock())
        result = await agent.create_situation(plot_brief_prev="Prev plot.")

        assert "plot_brief" in result
        assert "scene_direction" in result
        assert "instructions_out" in result

    @pytest.mark.asyncio
    async def test_create_situation_with_llm(self):
        from src.llm.dm_agent import DMAgent, _DM_SYSTEM_PROMPT

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
        from src.llm.dm_agent import DMAgent

        llm = MagicMock()
        llm.call_structured = AsyncMock(return_value=None)
        agent = DMAgent(llm)

        result = await agent.create_situation(plot_brief_prev="Test")

        assert "平静" in result["plot_brief"]
        assert result["instructions_out"] == []

    @pytest.mark.asyncio
    async def test_narrate_mock(self):
        from src.llm.dm_agent import DMAgent

        agent = DMAgent(AsyncMock())
        result = await agent.narrate(plot_brief="Test", character_actions=[])

        assert "narrative" in result
        assert "branch_points" in result
        assert "hooks_resolved" in result

    @pytest.mark.asyncio
    async def test_narrate_with_llm(self):
        from src.llm.dm_agent import DMAgent

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
        from src.llm.dm_agent import _DM_SYSTEM_PROMPT

        assert "Dungeon Master" in _DM_SYSTEM_PROMPT
        assert "不扮演任何角色" in _DM_SYSTEM_PROMPT


class TestDMSafety:
    """§13: DM 安全铁律测试."""

    @pytest.mark.asyncio
    async def test_dm_does_not_write_character_dialogue(self):
        """DM 不得写角色对话."""
        from src.llm.dm_agent import _DM_SYSTEM_PROMPT

        assert "不写角色的对话内容" in _DM_SYSTEM_PROMPT
        assert "不扮演任何角色" in _DM_SYSTEM_PROMPT
        assert "不替任何角色做决策" in _DM_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_dm_fallback_does_not_write_dialogue(self):
        """降级输出不得含角色对话引导."""
        from src.llm.dm_agent import DMAgent, _DM_SYSTEM_PROMPT

        agent = DMAgent(AsyncMock())
        result = await agent.create_situation(plot_brief_prev="")

        # 降级 plot_brief 不含对话引导符（引号/冒号+说话）
        plot = result["plot_brief"]
        assert "：\"" not in plot
        assert ":\"" not in plot

    @pytest.mark.asyncio
    async def test_dm_output_has_no_action_decisions(self):
        """DM instruction 不含角色行为决策."""
        from src.llm.dm_agent import DMAgent

        llm = AsyncMock()
        from src.schemas.llm_output import DMOutput, SceneDirectionOutput
        llm.call_structured = AsyncMock(return_value=DMOutput(
            plot_brief="A storm approaches.",
            scene_direction=SceneDirectionOutput(featured_pcs=[], featured_actors=[]),
            instructions=[],
        ))
        agent = DMAgent(llm)
        result = await agent.create_situation()

        # DM 指定了参演人员但不决定他们做什么
        assert "scene_direction" in result
        # instructions 应该空或只有环境事件
        for inst in result.get("instructions_out", []):
            assert inst.get("type", "") != "pc_action"

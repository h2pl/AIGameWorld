"""Character Engine 单元测试 / Character Engine unit tests.

Mock LLM Golden Case，验证结构化输出 + 护栏。
"""
# ── Imports / 导入 ──

# ── 依赖 / Dependencies ──

from unittest.mock import AsyncMock

import pytest

from src.schemas.llm_output import CharacterActionSchema
from src.schemas.request import ActorDecideRequest, PCDecideRequest


class TestPCDecide:
    @pytest.mark.asyncio
    async def test_llm_returns_action(self):
        from src.engine.character.pc_decide import pc_decide

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CharacterActionSchema(
                action_type="talk", target="innkeeper", reasoning="打听消息。"
            )
        )
        result = await pc_decide(
            PCDecideRequest(pc_id="alex", plot_brief="战斗", tick=1), {"configurable": {"llm": llm}}
        )
        assert result.character_id == "alex"
        assert result.type == "talk"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_none(self):
        from src.engine.character.pc_decide import pc_decide

        result = await pc_decide(PCDecideRequest(pc_id="alex", plot_brief="", tick=0), None)
        assert result.type == "wait"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.engine.character.pc_decide import pc_decide

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=Exception("LLM down"))
        result = await pc_decide(
            PCDecideRequest(pc_id="alex", plot_brief="", tick=0), {"configurable": {"llm": llm}}
        )
        assert result.type == "wait"

    @pytest.mark.asyncio
    async def test_guardrail_fixes_invalid_action(self):
        from src.engine.character.pc_decide import pc_decide

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CharacterActionSchema(action_type="dance", target=None, reasoning="跳舞。")
        )
        result = await pc_decide(
            PCDecideRequest(pc_id="alex", plot_brief="", tick=0), {"configurable": {"llm": llm}}
        )
        assert result.type == "wait"

    @pytest.mark.asyncio
    async def test_guardrail_fills_empty_reasoning(self):
        from src.engine.character.pc_decide import pc_decide

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CharacterActionSchema(action_type="move", target=None, reasoning="")
        )
        result = await pc_decide(
            PCDecideRequest(pc_id="alex", plot_brief="", tick=0), {"configurable": {"llm": llm}}
        )
        assert len(result.description) > 0


class TestActorDecide:
    @pytest.mark.asyncio
    async def test_llm_returns_action(self):
        from src.engine.character.actor_decide import actor_decide

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CharacterActionSchema(
                action_type="talk", target="alex", reasoning="推销货物。"
            )
        )
        result = await actor_decide(
            ActorDecideRequest(actor_id="innkeeper", plot_brief="", tick=0),
            {"configurable": {"llm": llm}},
        )
        assert result.character_id == "innkeeper"
        assert result.type == "talk"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_none(self):
        from src.engine.character.actor_decide import actor_decide

        result = await actor_decide(
            ActorDecideRequest(actor_id="innkeeper", plot_brief="", tick=0), None
        )
        assert result.type == "idle"
# ── END / 结束 ──

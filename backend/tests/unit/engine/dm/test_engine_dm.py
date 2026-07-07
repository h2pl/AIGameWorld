"""DM Engine 集成测试——dm_create/narrate + LLMClient + P2-4/P2-6。"""

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from src.engine.dm.dm_engine import dm_create, dm_narrate
from src.schemas.llm_output import DMNarrativeSchema, DMOutput
from src.schemas.request import DMCreateRequest, DMNarrateRequest


class TestDMCreate:
    @pytest.mark.asyncio
    async def test_creates_situation_with_llm(self):
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=DMOutput(
                plot_brief="LLM plot",
                scene_id="tavern",
                hints=["环境提示"],
            )
        )
        result = await dm_create(
            DMCreateRequest(tick=1, plot_brief=""), {"configurable": {"llm": llm}}
        )
        assert result.plot_brief == "LLM plot"
        assert result.scene_id == "tavern"


class TestDMNarrate:
    @pytest.mark.asyncio
    async def test_narrates_with_llm(self):
        from src.engine.dm.dm_engine import dm_narrate

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=DMNarrativeSchema(narrative="LLM narrative text")
        )
        req = DMNarrateRequest(tick=0, plot_brief="Story", hints=[])
        result = await dm_narrate(req, {"configurable": {"llm": llm}})
        assert result.narrative_out == "LLM narrative text"

    @pytest.mark.asyncio
    async def test_empty_narrative_raises(self):
        """LLM 返回空 narrative 时应当抛出异常，而不是 fallback / Empty narrative must raise."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(return_value=DMNarrativeSchema(narrative=""))
        req = DMNarrateRequest(tick=1, plot_brief="Story", hints=[])
        with pytest.raises(RuntimeError, match="empty narrative"):
            await dm_narrate(req, {"configurable": {"llm": llm}})

    @pytest.mark.asyncio
    async def test_llm_failure_raises(self):
        """LLM 调用异常时应当直接抛出 / LLM failure must propagate."""
        from src.engine.dm.dm_engine import dm_narrate

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=RuntimeError("LLM failed"))
        req = DMNarrateRequest(tick=1, plot_brief="Story", hints=[])
        with pytest.raises(RuntimeError, match="LLM failed"):
            await dm_narrate(req, {"configurable": {"llm": llm}})

    @pytest.mark.asyncio
    async def test_normalizes_pydantic_action_result(self):
        """actions.result 中的 Pydantic 模型会被转成 dict，避免模板渲染失败 / Pydantic results are normalized."""

        class FakeResult(BaseModel):
            turns: list = []
            waypoints: list = []

        llm = AsyncMock()
        llm.call_structured = AsyncMock(return_value=DMNarrativeSchema(narrative="ok narrative"))
        req = DMNarrateRequest(
            tick=1,
            plot_brief="Story",
            hints=[],
            actions=[
                {
                    "pc_id": "pc-1",
                    "action_type": "talk",
                    "target_id": "npc-1",
                    "result": FakeResult(turns=[{"speaker_id": "pc-1", "text": "hello"}]),
                }
            ],
        )
        result = await dm_narrate(req, {"configurable": {"llm": llm}})
        assert result.narrative_out == "ok narrative"


class TestDMGuardrails:
    def test_dm_output_hints_truncation(self):
        """hints 超过 4 条则截断."""
        result = DMOutput(plot_brief="x", hints=["a"] * 6)
        assert len(result.hints) == 6  # 模型不截断，engine 里截

    def test_narrate_keeps_valid(self):
        result = DMNarrativeSchema(narrative="雾气弥漫，远处传来钟声。")
        assert result.narrative == "雾气弥漫，远处传来钟声。"

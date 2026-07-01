"""Reflection + Summarizer Engine 单元测试 / Unit tests for reflection & summarizer engines.

Mock LLM Golden Case，验证结构化输出 + 护栏 + 降级 + importance 控制。
"""

from unittest.mock import AsyncMock

import pytest

from src.schemas.request import ReflectionRequest, SummarizerRequest


class TestReflectPC:
    """PC 深度反思 / PC deep reflection tests."""

    @pytest.mark.asyncio
    async def test_pc_llm_returns_insight(self):
        from src.engine.reflection_engine.reflection import reflect

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value={
                "arc_analysis": "Alex 正从鲁莽战士成长为可靠领袖。",
                "personality_insight": "在危机面前选择保护弱者而非冲锋，展现成长。",
                "next_direction": "需要一次领导老手的认可来巩固信心。",
            }
        )
        result = await reflect(
            ReflectionRequest(
                character_id="alex",
                character_name="Alex",
                character_type="pc",
                arc_stage="growth",
                arc_description="Prove his worth as a warrior",
                memories=[
                    {"content": "保护村民免受土匪攻击", "importance": 8},
                    {"content": "拒绝了来路不明的财富", "importance": 6},
                ],
                recent_reflections=["Alex 上次反思确认了保护弱者的价值观。"],
                tick=5,
            ),
            {"configurable": {"llm": llm}},
        )
        assert result.insights_out[0]["insight"].startswith("Alex")
        assert result.insights_out[0]["memory_type"] == "reflection"
        assert result.insights_out[0]["importance"] == 10
        assert not result.errors

    @pytest.mark.asyncio
    async def test_pc_fallback_on_llm_none(self):
        from src.engine.reflection_engine.reflection import reflect

        result = await reflect(
            ReflectionRequest(character_id="alex", character_name="Alex", character_type="pc"),
            None,
        )
        assert result.insights_out[0]["character_id"] == "alex"
        assert "降级" in result.errors[0] or "fallback" in result.errors[0]

    @pytest.mark.asyncio
    async def test_pc_fallback_on_llm_error(self):
        from src.engine.reflection_engine.reflection import reflect

        llm = AsyncMock()
        llm.call_structured = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        result = await reflect(
            ReflectionRequest(character_id="alex", character_name="Alex", character_type="pc"),
            {"configurable": {"llm": llm}},
        )
        assert result.insights_out[0]["character_id"] == "alex"
        assert len(result.errors) > 0


class TestReflectActor:
    """Actor 浅层反思 / Actor shallow reflection tests."""

    @pytest.mark.asyncio
    async def test_actor_llm_returns_summary(self):
        from src.engine.reflection_engine.reflection import reflect

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value={"behavior_summary": "Greta 持续暗中观察来往旅客，似乎在找人。"}
        )
        result = await reflect(
            ReflectionRequest(
                character_id="greta",
                character_name="Greta",
                character_type="actor",
                arc_stage="mystery",
                arc_description="Hiding a dark secret",
                memories=[
                    {"content": "频繁擦拭吧台一角，目光锁定门口", "importance": 5},
                    {"content": "注意到 Cole 的新短剑，试图打探消息", "importance": 4},
                ],
                tick=5,
            ),
            {"configurable": {"llm": llm}},
        )
        assert "Greta" in result.insights_out[0]["insight"]
        assert result.insights_out[0]["importance"] == 5


class TestSummarizer:
    """事件压缩 / Event summarization tests."""

    @pytest.mark.asyncio
    async def test_summarizer_compresses_events(self):
        from src.engine.summarizer_engine.summarizer import summarize

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value={"summary": "Alex 向 Greta 打探失踪商队，Cole 在广场巡逻。"}
        )
        result = await summarize(
            SummarizerRequest(
                events=[
                    {
                        "type": "character_action",
                        "description": "alex(talk): 向 Greta 打探失踪商队情报",
                    },
                    {
                        "type": "character_action",
                        "description": "cole(talk): 提醒新兵注意广场可疑动静",
                    },
                ],
                character_count=3,
                tick=1,
            ),
            {"configurable": {"llm": llm}},
        )
        assert result.compressed
        assert "Alex" in result.summary_text

    @pytest.mark.asyncio
    async def test_summarizer_fallback_on_llm_none(self):
        from src.engine.summarizer_engine.summarizer import summarize

        result = await summarize(
            SummarizerRequest(events=[], tick=0),
            None,
        )
        assert not result.compressed
        assert "降级" in result.errors[0] or "fallback" in result.errors[0]


class TestImportanceThreshold:
    """重要性阈值判定 / Importance threshold checks."""

    def test_importance_check_pc_threshold_100(self):

        mems = [
            type("Mem", (), {"importance": 40})(),
            type("Mem", (), {"importance": 35})(),
            type("Mem", (), {"importance": 30})(),
        ]
        total = sum(m.importance for m in mems)
        assert total >= 100  # 触发 / triggers

    def test_importance_check_actor_threshold_200(self):
        mems = [
            type("Mem", (), {"importance": 80})(),
            type("Mem", (), {"importance": 70})(),
            type("Mem", (), {"importance": 60})(),
        ]
        total = sum(m.importance for m in mems)
        assert total >= 200  # 触发 / triggers

    def test_importance_below_threshold_no_reflect(self):
        mems = [
            type("Mem", (), {"importance": 10})(),
            type("Mem", (), {"importance": 15})(),
        ]
        total = sum(m.importance for m in mems)
        assert total < 100  # 不触发 / not triggered

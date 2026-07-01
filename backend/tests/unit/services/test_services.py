"""Services 测试——State ↔ Engine adapter 层."""

from unittest.mock import AsyncMock, patch

import pytest

from src.services import (
    character_service,
    dm_service,
    reflection_service,
    scene_service,
    summarizer_service,
)


def _base_state(**overrides):
    return {
        "tick": 0,
        "hints": [],
        "plot_brief": "",
        "scene_id": "",
        "scene_events": [],
        "character_actions": [],
        "engine_results": [],
        "combat_result": None,
        "state_diff": {},
        "cast_changes": [],
        "narrative": "",
        "branch_points": [],
        "hooks_resolved": [],
        "reflected_characters": [],
        "summary_compressed": False,
        "errors": [],
        "needs_reflection": False,
        **overrides,
    }


# ============================================================
# World Service
# ============================================================
class TestWorldService:
    @pytest.mark.asyncio
    async def test_process_scene_with_hints(self):
        state = _base_state(hints=["探索酒馆", "与NPC交谈"])
        result = await scene_service.process_scene(state)
        # 事件已直接写 DB，state 不再 accumulate
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_process_scene_empty(self):
        state = _base_state()
        result = await scene_service.process_scene(state)
        assert isinstance(result, dict)


# ============================================================
# State Update Service
# ============================================================


# ============================================================
# Character Service（S3: async + Mock Golden Case）
# ============================================================
class TestCharacterService:
    @pytest.mark.asyncio
    async def test_pc_decide_no_pcs(self):
        state = {"tick": 0, "plot_brief": "", "pc_ids": [], "character_actions": []}
        result = await character_service.pc_decide(state, {"configurable": {}})
        assert result["character_actions"] == []

    @pytest.mark.asyncio
    async def test_pc_decide_with_llm(self):
        from src.schemas.response import PCDecideResponse

        state = {
            "tick": 0,
            "plot_brief": "战斗",
            "character_actions": [],
            "pc_ids": ["alex"],
        }
        with patch("src.services.character_service.pc_engine.pc_decide") as mock:
            mock.return_value = PCDecideResponse(
                character_id="alex",
                type="attack",
                description="攻击敌人！",
            )
            result = await character_service.pc_decide(state)
        assert len(result["character_actions"]) == 1
        assert result["character_actions"][0]["character_id"] == "alex"

    @pytest.mark.asyncio
    async def test_actor_decide_with_llm(self):
        from src.schemas.response import ActorDecideResponse

        state = {
            "tick": 0,
            "plot_brief": "",
            "character_actions": [],
            "actor_ids": ["innkeeper"],
        }
        with patch("src.services.character_service.actor_engine.actor_decide") as mock:
            mock.return_value = ActorDecideResponse(
                character_id="innkeeper",
                type="talk",
                description="推销货物",
            )
            result = await character_service.actor_decide(state)
        assert len(result["character_actions"]) == 1


# ============================================================
# Reflection / Summarizer Service
# ============================================================
class TestReflectionService:
    @pytest.mark.asyncio
    async def test_reflection_returns_insights(self):
        state = {
            "tick": 5,
            "character_id": "pc1",
            "memories": [],
            "events": [],
            "reflected_characters": [],
            "summary_compressed": False,
        }
        result = await reflection_service.reflect(state, None)
        assert "reflected_characters" in result


class TestSummarizerService:
    @pytest.mark.asyncio
    async def test_summarizer_returns_result(self):
        state = {
            "tick": 10,
            "character_id": "",
            "memories": [],
            "events": [{"id": "e1"}],
            "reflected_characters": [],
            "summary_compressed": False,
        }
        result = await summarizer_service.summarize(state)
        assert "summary_compressed" in result


# ============================================================
# DM Service
# ============================================================
class TestDMService:
    def _config(self, llm=None):
        return {"configurable": {"llm": llm or AsyncMock()}}

    @pytest.mark.asyncio
    async def test_dm_create_returns_hints(self):
        mock_llm = AsyncMock()
        mock_llm.call_structured = AsyncMock(return_value=None)
        state = _base_state(tick=0, plot_brief="")

        from src.schemas.response import DMCreateResponse

        with patch("src.services.dm_service.dm_engine.dm_create") as mock_create:
            mock_create.return_value = DMCreateResponse(
                hints=["探索"],
                plot_brief="剧情",
                scene_id="tavern",
            )
            result = await dm_service.dm_create(state, self._config(mock_llm))
        assert result["hints"] == ["探索"]
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_dm_create_propagates_errors(self):
        state = _base_state()
        from src.schemas.response import DMCreateResponse

        with patch("src.services.dm_service.dm_engine.dm_create") as mock_create:
            mock_create.return_value = DMCreateResponse(errors=["LLM 调用失败"])
            result = await dm_service.dm_create(state, self._config())
        assert "LLM" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_dm_narrate_returns_narrative(self):
        state = _base_state(tick=0)
        from src.schemas.response import DMNarrateResponse

        with patch("src.services.dm_service.dm_engine.dm_narrate") as mock_narrate:
            mock_narrate.return_value = DMNarrateResponse(
                narrative_out="战斗开始！",
            )
            result = await dm_service.dm_narrate(state, self._config())
        assert result["narrative"] == "战斗开始！"

    @pytest.mark.asyncio
    async def test_dm_narrate_sets_needs_reflection(self):
        state = _base_state(tick=5)
        from src.schemas.response import DMNarrateResponse

        with patch("src.services.dm_service.dm_engine.dm_narrate") as mock_narrate:
            mock_narrate.return_value = DMNarrateResponse(narrative_out="反思时刻")
            result = await dm_service.dm_narrate(
                state,
                {"configurable": {"llm": AsyncMock(), "reflection_interval": 5}},
            )
        assert result["needs_reflection"] is True

"""Services 测试——State ↔ Engine adapter 层."""

from unittest.mock import AsyncMock, patch

import pytest

from src.services import (
    character_service,
    combat_service,
    dialogue_service,
    dm_service,
    exploration_service,
    quest_service,
    reflection_service,
    state_update_service,
    summarizer_service,
    world_service,
)


def _base_state(**overrides):
    return {
        "tick": 0,
        "dm_instructions": [],
        "plot_brief": "",
        "scene_direction": {},
        "world_events": [],
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
    def test_world_update_with_instructions(self):
        state = _base_state(dm_instructions=["探索酒馆", "与NPC交谈"])
        result = world_service.world_update(state)
        assert len(result["world_events"]) == 2
        assert result["world_events"][0]["type"] == "dm_instruction"

    def test_world_update_empty(self):
        state = _base_state()
        result = world_service.world_update(state)
        assert result["world_events"] == []


# ============================================================
# State Update Service
# ============================================================
class TestStateUpdateService:
    def test_state_update_returns_diff_and_cast(self):
        result = state_update_service.state_update(_base_state())
        assert "state_diff" in result
        assert "cast_changes" in result
        assert isinstance(result["cast_changes"], list)


# ============================================================
# Character Service（S3: async + Mock Golden Case）
# ============================================================
class TestCharacterService:
    @pytest.mark.asyncio
    async def test_pc_decide_no_featured_pcs(self):
        state = {"tick": 0, "plot_brief": "", "scene_direction": {}, "character_actions": []}
        result = await character_service.pc_decide(state, {"configurable": {}})
        assert result["character_actions"] == []

    @pytest.mark.asyncio
    async def test_pc_decide_with_llm(self):
        from src.schemas.response import PCDecideResponse

        state = {
            "tick": 0, "plot_brief": "战斗", "character_actions": [],
            "scene_direction": {"featured_pcs": ["alex"]},
        }
        with patch("src.services.character_service.pc_engine.pc_decide") as mock:
            mock.return_value = PCDecideResponse(
                character_id="alex", type="attack", description="攻击敌人！",
            )
            result = await character_service.pc_decide(state)
        assert len(result["character_actions"]) == 1
        assert result["character_actions"][0]["character_id"] == "alex"

    @pytest.mark.asyncio
    async def test_actor_decide_with_llm(self):
        from src.schemas.response import ActorDecideResponse

        state = {
            "tick": 0, "plot_brief": "", "character_actions": [],
            "scene_direction": {"featured_actors": ["innkeeper"]},
        }
        with patch("src.services.character_service.actor_engine.actor_decide") as mock:
            mock.return_value = ActorDecideResponse(
                character_id="innkeeper", type="talk", description="推销货物",
            )
            result = await character_service.actor_decide(state)
        assert len(result["character_actions"]) == 1


# ============================================================
# Engine Services (Mock)
# ============================================================
class TestCombatService:
    def test_combat_returns_result(self):
        state = {"participants": [], "round": 1, "speaker": "", "target": "",
                 "intent": "", "character_id": "", "action_type": "", "quests": [],
                 "event_log": [], "engine_results": [], "combat_result": None}
        result = combat_service.combat(state)
        assert "engine_results" in result


class TestDialogueService:
    def test_dialogue_returns_result(self):
        state = {"participants": [], "round": 1, "speaker": "pc1", "target": "npc1",
                 "intent": "persuade", "character_id": "", "action_type": "",
                 "quests": [], "event_log": [], "engine_results": [], "combat_result": None}
        result = dialogue_service.dialogue(state)
        assert "engine_results" in result


class TestExplorationService:
    def test_exploration_returns_result(self):
        state = {"participants": [], "round": 1, "speaker": "", "target": "",
                 "intent": "", "character_id": "pc1", "action_type": "search",
                 "quests": [], "event_log": [], "engine_results": [], "combat_result": None}
        result = exploration_service.exploration(state)
        assert "engine_results" in result


class TestQuestService:
    def test_quest_returns_result(self):
        state = {"participants": [], "round": 1, "speaker": "", "target": "",
                 "intent": "", "character_id": "", "action_type": "",
                 "quests": [{"id": "q1"}], "event_log": [], "engine_results": [], "combat_result": None}
        result = quest_service.quest(state)
        assert "engine_results" in result


# ============================================================
# Reflection / Summarizer Service
# ============================================================
class TestReflectionService:
    def test_reflection_returns_insights(self):
        state = {"tick": 5, "character_id": "pc1", "memories": [], "events": [],
                 "reflected_characters": [], "summary_compressed": False}
        result = reflection_service.reflect(state)
        assert "reflected_characters" in result


class TestSummarizerService:
    def test_summarizer_returns_result(self):
        state = {"tick": 10, "character_id": "", "memories": [],
                 "events": [{"id": "e1"}], "reflected_characters": [], "summary_compressed": False}
        result = summarizer_service.summarize(state)
        assert "summary_compressed" in result


# ============================================================
# DM Service
# ============================================================
class TestDMService:
    def _config(self, llm=None):
        return {"configurable": {"llm": llm or AsyncMock()}}

    @pytest.mark.asyncio
    async def test_dm_create_returns_instructions(self):
        mock_llm = AsyncMock()
        mock_llm.call_structured = AsyncMock(return_value=None)
        state = _base_state(tick=0, plot_brief="")

        from src.schemas.response import DMCreateResponse
        with patch("src.services.dm_service.dm_engine.dm_create") as mock_create:
            mock_create.return_value = DMCreateResponse(
                instructions_out=["探索"], plot_brief="剧情", scene_direction={"mood": "tense"},
            )
            result = await dm_service.dm_create(state, self._config(mock_llm))
        assert result["dm_instructions"] == ["探索"]
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
        state = _base_state(tick=0, character_actions=[])
        from src.schemas.response import DMNarrateResponse
        with patch("src.services.dm_service.dm_engine.dm_narrate") as mock_narrate:
            mock_narrate.return_value = DMNarrateResponse(
                narrative_out="战斗开始！", branch_points=[{"decision_maker": "alex"}],
                hooks_resolved=["hook_01"],
            )
            result = await dm_service.dm_narrate(state, self._config())
        assert result["narrative"] == "战斗开始！"

    @pytest.mark.asyncio
    async def test_dm_narrate_sets_needs_reflection(self):
        state = _base_state(tick=5, character_actions=[])
        from src.schemas.response import DMNarrateResponse
        with patch("src.services.dm_service.dm_engine.dm_narrate") as mock_narrate:
            mock_narrate.return_value = DMNarrateResponse(narrative_out="反思时刻")
            result = await dm_service.dm_narrate(
                state, {"configurable": {"llm": AsyncMock(), "reflection_interval": 5}},
            )
        assert result["needs_reflection"] is True

"""Services 测试——State ↔ Engine adapter 层."""
import pytest

from src.services import (
    world_service, state_update_service,
    character_service, combat_service, dialogue_service,
    exploration_service, quest_service,
    reflection_service, summarizer_service,
)


def _base_state(**overrides):
    return {
        "tick": 0, "dm_instructions": [], "plot_brief": "", "scene_direction": {},
        "world_events": [], "character_actions": [], "engine_results": [],
        "combat_result": None, "state_diff": {}, "cast_changes": [],
        "narrative": "", "reflected_characters": [],
        "summary_compressed": False, "errors": [], "needs_reflection": False,
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
# Character Service
# ============================================================
class TestCharacterService:
    def test_pc_decide_no_featured_pcs(self):
        state = {"tick": 0, "plot_brief": "", "scene_direction": {}, "character_actions": []}
        result = character_service.pc_decide(state)
        assert result["character_actions"] == []

    def test_pc_decide_with_featured_pcs(self):
        state = {"tick": 0, "plot_brief": "战斗",
                 "scene_direction": {"featured_pcs": ["pc1", "pc2"]},
                 "character_actions": []}
        result = character_service.pc_decide(state)
        assert len(result["character_actions"]) == 2
        assert result["character_actions"][0]["character_id"] == "pc1"

    def test_actor_decide_with_featured_actors(self):
        state = {"tick": 0, "plot_brief": "",
                 "scene_direction": {"featured_actors": ["npc_guard"]},
                 "character_actions": []}
        result = character_service.actor_decide(state)
        assert len(result["character_actions"]) == 1


# ============================================================
# Engine Services (Mock)
# ============================================================
class TestCombatService:
    def test_combat_returns_result(self):
        state = {"participants": [], "round": 1, "speaker": "", "target": "",
                 "intent": "", "character_id": "", "action_type": "",
                 "quests": [], "event_log": [], "engine_results": [], "combat_result": None}
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
        state = {"tick": 5, "character_id": "pc1", "memories": [],
                 "events": [], "reflected_characters": [], "summary_compressed": False}
        result = reflection_service.reflection(state)
        assert "reflected_characters" in result


class TestSummarizerService:
    def test_summarizer_returns_result(self):
        state = {"tick": 10, "character_id": "", "memories": [],
                 "events": [{"id": "e1"}], "reflected_characters": [], "summary_compressed": False}
        result = summarizer_service.summarizer(state)
        assert "summary_compressed" in result

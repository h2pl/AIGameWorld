"""Engine 单元测试——combat/dialogue/exploration/quest/reflection/summarizer/world."""

from src.engine.combat.combat import resolve_combat
from src.engine.dialogue.dialogue import resolve_dialogue
from src.engine.exploration.exploration import resolve_exploration
from src.engine.quest.quest import check_quests
from src.engine.reflection.reflection import reflect
from src.engine.summarizer.summarizer import summarize
from src.engine.world.world import execute_instructions
from src.schemas.request import (
    CombatRequest,
    DialogueRequest,
    ExplorationRequest,
    QuestRequest,
    ReflectionRequest,
    SummarizerRequest,
    WorldUpdateRequest,
)


class TestCombatEngine:
    def test_empty_participants(self):
        r = resolve_combat(CombatRequest(participants=[]))
        assert r.winner is None

    def test_with_participants(self):
        r = resolve_combat(CombatRequest(participants=["hero", "goblin"]))
        assert r.winner == "hero"
        assert len(r.combat_log) == 1


class TestDialogueEngine:
    def test_resolve_dialogue(self):
        r = resolve_dialogue(DialogueRequest(speaker="pc1", target="npc1", intent="persuade"))
        assert r.success is True
        assert "pc1" in r.content


class TestExplorationEngine:
    def test_resolve_exploration(self):
        r = resolve_exploration(ExplorationRequest(character_id="pc1", action_type="search"))
        assert r.success is True
        assert r.result["character_id"] == "pc1"


class TestQuestEngine:
    def test_no_quests(self):
        r = check_quests(QuestRequest())
        assert r.completed_ids == []

    def test_completed_quest(self):
        r = check_quests(QuestRequest(quests=[{"id": "q1", "completed": True}]))
        assert r.completed_ids == ["q1"]

    def test_only_uncompleted(self):
        r = check_quests(
            QuestRequest(quests=[{"id": "q1", "completed": False}, {"id": "q2", "completed": True}])
        )
        assert r.completed_ids == ["q2"]


class TestReflectionEngine:
    def test_reflect(self):
        r = reflect(ReflectionRequest(character_id="pc1", memories=[{"text": "a"}, {"text": "b"}]))
        assert len(r.insights_out) == 1
        assert r.insights_out[0]["memories_count"] == 2

    def test_reflect_unknown_character(self):
        r = reflect(ReflectionRequest())
        assert r.insights_out[0]["character_id"] == "unknown"


class TestSummarizerEngine:
    def test_few_events_not_compressed(self):
        r = summarize(SummarizerRequest(events=[{"id": "e1"}], tick=5))
        assert r.compressed is False

    def test_many_events_compressed(self):
        r = summarize(SummarizerRequest(events=[{"id": f"e{i}"} for i in range(5)], tick=10))
        assert r.compressed is True


class TestWorldEngine:
    def test_execute_instructions(self):
        r = execute_instructions(WorldUpdateRequest(tick=1, dm_instructions=["探索", "交谈"]))
        assert len(r.events_out) == 2
        assert r.events_out[0]["type"] == "dm_instruction"
        assert r.events_out[0]["tick"] == 1


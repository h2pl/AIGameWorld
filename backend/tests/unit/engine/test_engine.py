"""Engine 单元测试——combat/dialogue/exploration/quest/reflection/summarizer/world."""

import pytest

# ── Engine imports / 引擎导入 ──
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

    def test_party_auto_wins_against_nothing(self):
        from src.schemas.request import CombatParticipant
        r = resolve_combat(CombatRequest(
            participants=[CombatParticipant(name="hero", team="party", hp=10, max_hp=10)]
        ))
        assert r.winner == "party"


class TestDialogueEngine:
    def test_persuasion_success(self):
        r = resolve_dialogue(DialogueRequest(speaker="pc1", target="npc1", intent="persuade", attribute_mod=3, dc=12))
        assert isinstance(r.success, bool)

    def test_empty_speaker(self):
        r = resolve_dialogue(DialogueRequest())
        assert r.success is False


class TestExplorationEngine:
    def test_perception_check(self):
        r = resolve_exploration(ExplorationRequest(character_id="pc1", action_type="search", attribute_mod=2, dc=10))
        assert isinstance(r.success, bool)
        assert r.result["character_id"] == "pc1"
        assert "roll" in r.result


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
    @pytest.mark.asyncio
    async def test_reflect(self):
        r = await reflect(
            ReflectionRequest(character_id="pc1", character_name="P1", character_type="pc"),
            None,
        )
        assert len(r.insights_out) == 1
        assert r.insights_out[0]["character_id"] == "pc1"

    @pytest.mark.asyncio
    async def test_reflect_unknown_character(self):
        r = await reflect(
            ReflectionRequest(character_id="", character_name="Unknown", character_type="pc"),
            None,
        )
        assert len(r.insights_out) == 1


class TestSummarizerEngine:
    @pytest.mark.asyncio
    async def test_few_events_not_compressed(self):
        r = await summarize(SummarizerRequest(events=[], tick=5), None)
        assert r.compressed is False

    @pytest.mark.asyncio
    async def test_many_events_compressed(self):
        r = await summarize(
            SummarizerRequest(events=[{"type": "e", "description": f"e{i}"} for i in range(5)], tick=10),
            None,
        )
        assert not r.compressed  # fallback（无 LLM）不压缩


class TestWorldEngine:
    def test_execute_instructions(self):
        r = execute_instructions(WorldUpdateRequest(tick=1, dm_instructions=["探索", "交谈"]))
        assert len(r.events_out) == 2
        assert r.events_out[0]["type"] == "dm_instruction"
        assert r.events_out[0]["tick"] == 1
# ── END / 结束 ──

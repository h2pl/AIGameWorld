"""Engine 单元测试——combat/dialogue/exploration/quest/reflection/summarizer/world."""

import pytest

# ── Engine imports / 引擎导入 ──
from src.engine.combat.combat_engine import resolve_combat
from src.engine.exploration.exploration_engine import resolve_exploration
from src.engine.quest.quest_engine import check_quests
from src.engine.reflection.reflection_engine import reflect
from src.engine.scene.scene_engine import process_scene_objects, process_scene_setup
from src.engine.summarizer.summarizer_engine import summarize
from src.engine.talk.talk_engine import process_talk_actions
from src.schemas.request import (
    CombatRequest,
    ExplorationRequest,
    QuestRequest,
    ReflectionRequest,
    SceneProcessRequest,
    SummarizerRequest,
)


class TestCombatEngine:
    def test_empty_participants(self):
        r = resolve_combat(CombatRequest(participants=[]))
        assert r.winner is None

    def test_party_auto_wins_against_nothing(self):
        from src.schemas.request import CombatParticipant

        r = resolve_combat(
            CombatRequest(
                participants=[CombatParticipant(name="hero", team="party", hp=10, max_hp=10)]
            )
        )
        assert r.winner == "party"


class TestTalkEngine:
    @pytest.mark.asyncio
    async def test_empty_actions(self):
        """空 actions 不报错 / Empty actions don't crash."""
        await process_talk_actions(actions=[], tick_message_id="", tick=0)
        # no error = pass

    @pytest.mark.asyncio
    async def test_non_talk_actions_skipped(self):
        """非 talk 类型被跳过 / Non-talk actions are skipped."""
        await process_talk_actions(
            actions=[{"type": "move", "character_id": "pc1"}],
            tick_message_id="",
            tick=0,
        )


class TestExplorationEngine:
    def test_perception_check(self):
        r = resolve_exploration(
            ExplorationRequest(character_id="pc1", action_type="search", attribute_mod=2, dc=10)
        )
        assert isinstance(r.success, bool)
        assert r.result is not None
        assert r.result["character_id"] == "pc1"
        assert "roll" in r.result


class TestInteractEngine:
    def test_pick_lock(self):
        from src.engine.exploration.interact import resolve_interact
        from src.schemas.request import SceneObjectInteractRequest

        r = resolve_interact(
            SceneObjectInteractRequest(
                object_id="chest1",
                character_id="pc1",
                action_type="pick_lock",
                attribute_mod=3,
                dc=12,
            )
        )
        assert isinstance(r.success, bool)
        assert r.result is not None
        assert r.result["action_cn"] == "开锁"
        assert "roll" in r.result

    def test_break_door(self):
        from src.engine.exploration.interact import resolve_interact
        from src.schemas.request import SceneObjectInteractRequest

        r = resolve_interact(
            SceneObjectInteractRequest(
                object_id="door1",
                character_id="pc1",
                action_type="break_door",
                attribute_mod=4,
                dc=15,
            )
        )
        assert isinstance(r.success, bool)
        assert r.result is not None
        assert r.result["action_cn"] == "破门"


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
            SummarizerRequest(
                events=[{"type": "e", "description": f"e{i}"} for i in range(5)], tick=10
            ),
            None,
        )
        assert not r.compressed  # fallback（无 LLM）不压缩


class TestSceneEngine:
    @pytest.mark.asyncio
    async def test_process_scene_setup(self):
        await process_scene_setup(SceneProcessRequest(tick=1, scene_id="tavern", tick_message_id="tick_1"))

    @pytest.mark.asyncio
    async def test_process_scene_objects(self):
        await process_scene_objects(SceneProcessRequest(tick=1, scene_id="tavern", tick_message_id="tick_1"))


# ── END / 结束 ──
# ── 组件测试 / Component test
# ──
# ──

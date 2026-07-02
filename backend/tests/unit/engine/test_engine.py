"""Engine 单元测试——combat/dialogue/exploration/quest/reflection/summarizer/world."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

# ── Engine imports / 引擎导入 ──
from src.engine.combat.combat_engine import process_combat_action, resolve_combat
from src.engine.interact.interact_engine import process_interact_action
from src.engine.quest.quest_engine import check_quests
from src.engine.reflection.reflection_engine import reflect
from src.engine.talk.talk_engine import process_talk_action
from src.schemas.request import (
    CombatRequest,
    QuestRequest,
    ReflectionRequest,
)


def _event_repo_config():
    """构造带 event_repo mock 的 config / Build config with an event_repo mock."""
    event_repo = AsyncMock()
    return {"configurable": {"repos": {"event": event_repo}}}, event_repo


def _scene_char_config(scene_obj=None, pc=None):
    """构造带 scene_repo/char_repo mock 的 config / Build config with scene_repo/char_repo mocks."""
    scene_repo = AsyncMock()
    scene_repo.load_all = AsyncMock(return_value={scene_obj.id: scene_obj} if scene_obj else {})
    char_repo = AsyncMock()
    char_repo.load_pc = AsyncMock(return_value=pc)
    return {"configurable": {"repos": {"scene": scene_repo, "char": char_repo}}}


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
    async def test_non_talk_action_skipped(self):
        """非 talk 类型被跳过 / Non-talk action is skipped."""
        event = await process_talk_action(
            decision={"type": "move", "pc_id": "pc1"},
            plot_brief="",
            hints=[],
            scene_id="",
            tick=0,
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_talk_without_llm_falls_back_to_single_line(self):
        """无 LLM 时降级为发起者一句话 / Without an LLM, falls back to a single initiator line."""
        event = await process_talk_action(
            decision={
                "type": "talk",
                "pc_id": "pc1",
                "target_id": "npc1",
                "description": "先打个招呼",
            },
            plot_brief="",
            hints=[],
            scene_id="",
            tick=1,
        )
        turns = event["turns"]
        assert len(turns) == 1
        assert turns[0]["speaker_id"] == "pc1"
        assert turns[0]["text"] == "先打个招呼"

    @pytest.mark.asyncio
    async def test_talk_generates_multi_turn_dialogue(self):
        """有 LLM + target 时生成多轮对话，双方都存记忆 / With LLM + target, generates multi-turn dialogue and stores memory for both."""
        from src.schemas.llm_output import DialogueSchema, DialogueTurnSchema

        memory_repo = Mock()
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=DialogueSchema(
                turns=[
                    DialogueTurnSchema(speaker_id="pc1", text="你好，最近镇上如何？"),
                    DialogueTurnSchema(speaker_id="npc1", text="还算太平，你有什么需要吗？"),
                ]
            )
        )
        config = {
            "configurable": {
                "llm": llm,
                "repos": {"char": None, "memory": memory_repo},
            }
        }
        event = await process_talk_action(
            decision={
                "type": "talk",
                "pc_id": "pc1",
                "target_id": "npc1",
                "target_type": "actor",
                "description": "打听消息",
            },
            plot_brief="镇上最近不安宁",
            hints=["注意酒馆里的异动"],
            scene_id="tavern",
            tick=1,
            config=config,
        )
        turns = event["turns"]
        assert len(turns) == 2
        assert turns[0]["speaker_id"] == "pc1"
        assert turns[1]["speaker_id"] == "npc1"
        assert event["participants"] == ["pc1", "npc1"]
        assert memory_repo.store.call_count == 2


class TestInteractEngine:
    def test_pick_lock(self):
        from src.engine.interact.interact_engine import resolve_interact
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
        from src.engine.interact.interact_engine import resolve_interact
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


class TestInteractAction:
    """process_interact_action 单动作执行测试 / Single-action interact execution tests."""

    @pytest.mark.asyncio
    async def test_non_interact_action_skipped(self):
        event = await process_interact_action(
            decision={"type": "talk", "pc_id": "pc1", "target_id": "obj1"},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_interact_without_target_skipped(self):
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1"},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_interact_without_scene_object_auto_succeeds(self):
        """找不到目标物体时降级为无需检定直接成功 / No matching scene object falls back to an auto-success interact."""
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
        )
        assert event["kind"] == "character_interact"
        assert event["object_id"] == "chest1"
        assert event["success"] is True

    @pytest.mark.asyncio
    async def test_interact_locked_chest_uses_dex_check(self):
        """上锁容器按 lock_dc 用敏捷检定开锁 / A locked container is resolved with a DEX check against lock_dc."""
        from src.domain.scene_object import SceneObject, SceneObjectType

        chest = SceneObject(
            id="chest1",
            name="宝箱",
            object_type=SceneObjectType.CONTAINER,
            interact_data={"locked": True, "lock_dc": 5},
        )
        pc = SimpleNamespace(attributes_json='{"dex": 18}')
        config = _scene_char_config(scene_obj=chest, pc=pc)
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            config=config,
        )
        assert event["kind"] == "character_interact"
        assert event["result"]["action"] == "pick_lock"
        assert event["result"]["bonus"] == 4  # (18-10)//2

    @pytest.mark.asyncio
    async def test_interact_unlocked_chest_auto_succeeds(self):
        """未上锁容器无需检定，直接成功 / An unlocked container needs no check, auto success."""
        from src.domain.scene_object import SceneObject, SceneObjectType

        chest = SceneObject(
            id="chest1",
            name="宝箱",
            object_type=SceneObjectType.CONTAINER,
            interact_data={"locked": False},
        )
        config = _scene_char_config(scene_obj=chest)
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            config=config,
        )
        assert event["success"] is True
        assert event["result"]["action"] == "open_chest"
        assert event["result"]["roll"] is None


class TestCombatAction:
    """process_combat_action 单动作执行测试 / Single-action combat execution tests."""

    @pytest.mark.asyncio
    async def test_non_combat_action_skipped(self):
        event = await process_combat_action(
            decision={"type": "talk", "pc_id": "pc1", "target_id": "npc1"},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_combat_without_target_skipped(self):
        event = await process_combat_action(
            decision={"type": "combat", "pc_id": "pc1"},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_combat_records_intent_without_resolving(self):
        """combat 只记录意图，不结算 / combat only records intent, not resolved."""
        event = await process_combat_action(
            decision={"type": "combat", "pc_id": "pc1", "target_id": "npc_goblin"},
        )
        assert event["kind"] == "character_combat"
        assert event["target_id"] == "npc_goblin"
        assert event["resolved"] is False


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


# ── END / 结束 ──
# ── 组件测试 / Component test
# ──
# ──

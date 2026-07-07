"""Engine 单元测试——combat/dialogue/exploration/quest/reflection/summarizer/world."""

from unittest.mock import AsyncMock

import pytest

# ── Engine imports / 引擎导入 ──
from src.domain import Memory
from src.domain.actor import Actor
from src.domain.player_character import PlayerCharacter
from src.engine.combat.combat_engine import process_combat_action
from src.engine.interact.interact_engine import process_interact_action
from src.engine.quest.quest_engine import check_quests
from src.engine.reflection.reflection_engine import reflect
from src.engine.talk.talk_engine import process_talk_action
from src.schemas.request import (
    QuestRequest,
    ReflectionRequest,
)


def _event_repo_config():
    """构造带 event_repo mock 的 config / Build config with an event_repo mock."""
    event_repo = AsyncMock()
    return {"configurable": {"repos": {"event": event_repo}}}, event_repo


def _scene_char_config(scene_obj=None, pc=None, llm=None):
    """构造带 scene_repo/pc_repo/memory_repo mock 的 config / Build config with repo mocks."""
    scene_repo = AsyncMock()
    scene_repo.load_all = AsyncMock(return_value={scene_obj.id: scene_obj} if scene_obj else {})
    pc_repo = AsyncMock()
    pc_repo.load_one = AsyncMock(return_value=pc)
    memory_repo = AsyncMock()
    memory_repo.retrieve = AsyncMock(return_value=[])
    memory_repo.store = AsyncMock(return_value=None)
    cfg: dict = {
        "configurable": {"repos": {"scene": scene_repo, "char": pc_repo, "memory": memory_repo}}
    }
    if llm:
        cfg["configurable"]["llm"] = llm
    return cfg


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
    async def test_talk_generates_multi_turn_dialogue(self):
        """有 LLM + target 时生成多轮对话，PC 记忆写入 pc_memory_map / With LLM + target, generates multi-turn dialogue and stages memory."""
        from src.schemas.llm_output import DialogueSchema, DialogueTurnSchema

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
                "repos": {"char": None},
            }
        }
        pc_memory_map: dict[str, list[Memory]] = {}
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
            pc_memory_map=pc_memory_map,
            config=config,
        )
        turns = event.turns
        assert len(turns) == 2
        assert turns[0]["speaker_id"] == "pc1"
        assert turns[1]["speaker_id"] == "npc1"
        assert event.participants == ["pc1", "npc1"]
        # Actor 不记记忆，只有 PC 写入 pc_memory_map / Actors don't store memories
        assert len(pc_memory_map.get("pc1", [])) == 1
        assert pc_memory_map["pc1"][0].memory_type == "talk"


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
    async def test_interact_returns_kind_and_narration(self):
        """LLM 生成交互返回 success + narration / LLM generates interact with success + narration."""
        from src.domain.player_character import PlayerCharacter
        from src.domain.scene_object import SceneObject, SceneObjectType
        from src.schemas.llm_output import InteractOutputSchema

        chest = SceneObject(
            id="chest1",
            name="宝箱",
            object_type=SceneObjectType.CONTAINER,
            interact_data={"locked": False},
            position_x=5,
            position_y=5,
        )
        pc = PlayerCharacter(
            id="pc1",
            name="pc1",
            position_x=0,
            position_y=0,
        )
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=InteractOutputSchema(
                success=True,
                narration="他打开宝箱，金币的光芒照亮了脸庞。",
            )
        )
        config = _scene_char_config(scene_obj=chest, llm=llm)
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            scene={"map_width": 40, "map_height": 40},
            scene_objects=[
                {
                    "id": "chest1",
                    "name": "宝箱",
                    "object_type": "container",
                    "position_x": 5,
                    "position_y": 5,
                    "interact_data": {"locked": False},
                },
            ],
            pcs={"pc1": pc},
            config=config,
        )
        assert event.kind == "pc_interact"
        assert event.success is True
        assert "金币" in event.narration


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
    async def test_combat_moves_pc_adjacent_to_actor(self):
        """combat 将 PC 移动到目标 Actor 旁边 / Combat moves PC adjacent to target actor."""
        from src.schemas.llm_output import CombatNarrationSchema

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CombatNarrationSchema(narration="他一剑劈向地精。")
        )
        pcs = {
            "pc1": PlayerCharacter(
                id="pc1",
                name="pc1",
                position_x=0,
                position_y=0,
                combat_json='{"hp":10,"max_hp":10,"ac":12,"attack_bonus":2,"damage_dice":"1d8"}',
                attributes_json='{"strength":14,"dexterity":12}',
            ),
        }
        actors = {
            "goblin": Actor(
                id="goblin",
                name="地精",
                position_x=5,
                position_y=5,
                combat_json='{"hp":5,"max_hp":5,"ac":10,"attack_bonus":1,"damage_dice":"1d4"}',
                attributes_json='{"strength":10,"dexterity":10}',
            ),
        }
        event = await process_combat_action(
            decision={
                "type": "combat",
                "pc_id": "pc1",
                "target_id": "goblin",
                "target_type": "actor",
            },
            pcs=pcs,
            actors=actors,
            tick=1,
            config={"configurable": {"llm": llm}},
        )
        assert event.kind == "pc_combat"
        assert event.target_id == "goblin"
        assert len(event.waypoints) == 2
        final = event.waypoints[-1]
        assert abs(final["x"] - 5) <= 1 and abs(final["y"] - 5) <= 1
        assert pcs["pc1"].position_x == final["x"]
        assert pcs["pc1"].position_y == final["y"]

    @pytest.mark.asyncio
    async def test_combat_defeats_target_via_llm(self):
        """LLM 判定击败时同步更新 Actor 状态 / LLM defeat updates actor state."""
        from src.schemas.llm_output import CombatNarrationSchema

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CombatNarrationSchema(
                narration="他闪过敌人的攻击，反手刺出一剑。",
                target_defeated=True,
                result="地精被击败",
            )
        )
        pcs = {
            "pc1": PlayerCharacter(
                id="pc1",
                name="pc1",
                position_x=4,
                position_y=5,
                combat_json='{"hp":10,"max_hp":10,"ac":12,"attack_bonus":2,"damage_dice":"1d8"}',
                attributes_json='{"strength":14,"dexterity":12}',
            ),
        }
        actors = {
            "goblin": Actor(
                id="goblin",
                name="地精",
                position_x=5,
                position_y=5,
                combat_json='{"hp":5,"max_hp":5,"ac":10,"attack_bonus":1,"damage_dice":"1d4"}',
                attributes_json='{"strength":10,"dexterity":10}',
            ),
        }
        event = await process_combat_action(
            decision={
                "type": "combat",
                "pc_id": "pc1",
                "target_id": "goblin",
                "target_type": "actor",
            },
            pcs=pcs,
            actors=actors,
            tick=2,
            pc_memory_map={},
            config={"configurable": {"llm": llm}},
        )
        assert "反手刺出一剑" in event.narration
        assert event.target_defeated is True
        assert actors["goblin"].status == "dead"

    @pytest.mark.asyncio
    async def test_combat_stores_memory(self):
        """combat 结果写入 pc_memory_map / Combat result is staged into state memory map."""
        from src.schemas.llm_output import CombatNarrationSchema

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=CombatNarrationSchema(narration="他击中了敌人。")
        )
        pc_memory_map: dict[str, list[Memory]] = {}
        pcs = {
            "pc1": PlayerCharacter(
                id="pc1",
                name="pc1",
                position_x=4,
                position_y=5,
                combat_json='{"hp":10,"max_hp":10,"ac":12,"attack_bonus":2,"damage_dice":"1d8"}',
                attributes_json='{"strength":14,"dexterity":12}',
            ),
        }
        actors = {
            "goblin": Actor(
                id="goblin",
                name="地精",
                position_x=5,
                position_y=5,
                combat_json='{"hp":5,"max_hp":5,"ac":10,"attack_bonus":1,"damage_dice":"1d4"}',
                attributes_json='{"strength":10,"dexterity":10}',
            ),
        }
        await process_combat_action(
            decision={
                "type": "combat",
                "pc_id": "pc1",
                "target_id": "goblin",
                "target_type": "actor",
            },
            pcs=pcs,
            actors=actors,
            tick=3,
            pc_memory_map=pc_memory_map,
            config={"configurable": {"llm": llm}},
        )
        assert len(pc_memory_map.get("pc1", [])) == 1
        mem = pc_memory_map["pc1"][0]
        assert mem.memory_type == "combat"
        assert mem.tick == 3


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
        from src.schemas.llm_output import ReflectionOutputSchema

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=ReflectionOutputSchema(
                arc_analysis="弧线推进", personality_insight="性格更坚毅"
            )
        )
        config = {"configurable": {"llm": llm}}
        r = await reflect(
            ReflectionRequest(pc_id="pc1", pc_name="P1", pc_type="pc"),
            config,
        )
        assert len(r.insights_out) == 1
        assert r.insights_out[0]["pc_id"] == "pc1"

    @pytest.mark.asyncio
    async def test_reflect_unknown_character(self):
        from src.schemas.llm_output import ReflectionOutputSchema

        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=ReflectionOutputSchema(arc_analysis="", personality_insight="")
        )
        config = {"configurable": {"llm": llm}}
        r = await reflect(
            ReflectionRequest(pc_id="", pc_name="Unknown", pc_type="pc"),
            config,
        )
        assert len(r.insights_out) == 1


# ── END / 结束 ──
# ── 组件测试 / Component test
# ──
# ──

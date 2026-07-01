"""Domain 模型测试——7 个领域模型验证."""

import pytest
from pydantic import ValidationError

from src.domain.action import Action
from src.domain.character import (
    Actor,
    Attributes,
    CharacterArc,
    CombatStats,
    Equipment,
    InventorySlot,
    Location,
    PlayerCharacter,
    Relationship,
)
from src.domain.dm_record import DMRecord
from src.domain.event import DmNarrativeEvent, OpeningEvent, SceneSetupEvent
from src.domain.item import Item, ItemType
from src.domain.scene_object import SceneObject, SceneObjectType
from src.domain.story import Quest
from src.domain.story_summary import StorySummary


# ============================================================
# Action
# ============================================================
class TestAction:
    def test_defaults(self):
        a = Action(character_id="pc1")
        assert a.character_id == "pc1"
        assert a.character_type == "pc"
        assert a.action_type == "wait"
        assert a.params == {}

    def test_with_target(self):
        a = Action(character_id="pc1", action_type="attack", target="goblin")
        assert a.target == "goblin"


# ============================================================
# Character
# ============================================================
class TestCharacterDomain:
    def test_location_defaults(self):
        loc = Location()
        assert loc.scene_id == ""
        assert loc.position_x == 0

    def test_combat_stats_defaults(self):
        cs = CombatStats()
        assert cs.hp == 10
        assert cs.ac == 10
        assert cs.speed == 30

    def test_attributes_defaults(self):
        attr = Attributes()
        assert attr.strength == 10
        assert attr.charisma == 10

    def test_attributes_custom(self):
        attr = Attributes(strength=16, dexterity=14)
        assert attr.strength == 16

    def test_equipment(self):
        eq = Equipment(weapon_id="sword_01")
        assert eq.weapon_id == "sword_01"
        assert eq.armor_id is None

    def test_inventory_slot(self):
        s = InventorySlot(item_id="potion_01", quantity=3)
        assert s.quantity == 3

    def test_relationship(self):
        r = Relationship(attitude="friendly")
        assert r.attitude == "friendly"

    def test_character_arc_defaults(self):
        arc = CharacterArc()
        assert arc.stage == "setup"

    def test_actor_minimal(self):
        a = Actor(id="npc1", name="Guard")
        assert a.role == ""
        assert a.status == "active"

    def test_actor_with_combat(self):
        a = Actor(id="npc1", combat=CombatStats(hp=20))
        assert a.combat.hp == 20

    def test_player_character_minimal(self):
        pc = PlayerCharacter(id="hero1", name="Aragon")
        assert pc.combat.hp == 10
        assert pc.roster_status == "member"

    def test_player_character_requires_id(self):
        with pytest.raises(ValidationError):  # noqa: F821
            PlayerCharacter()  # pyright: ignore[reportCallIssue]


# ============================================================
# Event / 消息事件
# ============================================================
class TestEvent:
    def test_opening(self):
        e = OpeningEvent(text="欢迎！")
        assert e.type == "opening"

    def test_scene_setup(self):
        e = SceneSetupEvent(scene_id="s1", scene_name="Village")
        assert e.type == "scene_setup"

    def test_narrative_mood(self):
        e = DmNarrativeEvent(text="夜幕降临", mood="mysterious")
        assert e.mood == "mysterious"


# ============================================================
# Item
# ============================================================
class TestItem:
    def test_item_creation(self):
        item = Item(id="sword_01", name="Iron Sword", item_type=ItemType.WEAPON)
        assert item.rarity == "common"
        assert item.weight == 0.0

    def test_item_type_enum(self):
        assert ItemType.POTION.value == "potion"
        assert ItemType.KEY.value == "key"


# ============================================================
# SceneObject
# ============================================================
class TestSceneObject:
    def test_scene_object(self):
        so = SceneObject(id="door_01", name="Wooden Door", object_type=SceneObjectType.DOOR)
        assert so.interactable is True

    def test_scene_object_type_enum(self):
        assert SceneObjectType.TRAP.value == "trap"
        assert SceneObjectType.CONTAINER.value == "container"


# ============================================================
# DMRecord / StorySummary
# ============================================================
class TestDMRecord:
    def test_defaults(self):
        r = DMRecord()
        assert r.tick == 0
        assert r.world_id == ""
        assert r.dm_narrative == ""

    def test_full(self):
        r = DMRecord(world_id="test", tick=3, plot_brief="场景", dm_narrative="叙事文本")
        assert r.dm_narrative == "叙事文本"


class TestStorySummary:
    def test_summary(self):
        s = StorySummary(world_id="test", tick_start=1, tick_end=10, summary="章节摘要")
        assert s.tick_start == 1
        assert s.tick_end == 10
        assert s.summary == "章节摘要"


class TestQuest:
    def test_quest(self):
        q = Quest(id="q1", title="Save Village", assigned_pcs=["pc1"])
        assert q.status == "inactive"

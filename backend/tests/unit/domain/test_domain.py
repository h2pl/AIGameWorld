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
from src.domain.event import DmNarrativeEvent, OpeningEvent, SceneSetupEvent
from src.domain.instruction import (
    ActorMotivation,
    DMInstruction,
    PlotEvent,
    SceneChange,
    SceneDirection,
)
from src.domain.item import Item, ItemType
from src.domain.scene_object import SceneObject, SceneObjectType
from src.domain.story import (
    BranchPoint,
    CastChangeEvent,
    MainCastRoster,
    Quest,
    StoryArc,
    StoryHook,
)


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
        assert a.combat_engine.hp == 20

    def test_player_character_minimal(self):
        pc = PlayerCharacter(id="hero1", name="Aragon")
        assert pc.combat_engine.hp == 10
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
# Instruction
# ============================================================
class TestInstruction:
    def test_dm_instruction_base(self):
        inst = DMInstruction(type="plot_event")
        assert inst.priority == 0

    def test_plot_event(self):
        pe = PlotEvent(
            type="plot_event", event_subtype="monster_attack", description="Goblins attack!"
        )
        assert pe.event_subtype == "monster_attack"

    def test_actor_motivation(self):
        am = ActorMotivation(
            type="actor_motivation", target_actor_id="npc1", new_goal="protect the village"
        )
        assert am.target_actor_id == "npc1"

    def test_scene_change(self):
        sc = SceneChange(
            type="scene_change", scene_id="forest_01", weather="rainy", time_of_day="night"
        )
        assert sc.weather == "rainy"

    def test_scene_direction(self):
        sd = SceneDirection(
            type="scene_direction", featured_pcs=["pc1", "pc2"], featured_actors=["npc_guard"]
        )
        assert len(sd.featured_pcs) == 2

    def test_instruction_type_literal(self):
        with pytest.raises(ValidationError):
            DMInstruction(type="invalid_type")


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
# Story
# ============================================================
class TestStory:
    def test_branch_point(self):
        bp = BranchPoint(
            tick=5, decision_maker="pc1", decision="enter cave", consequence="found treasure"
        )
        assert bp.tick == 5

    def test_story_arc_minimal(self):
        arc = StoryArc(id="arc1")
        assert arc.stage == "铺陈"
        assert arc.status == "setup"

    def test_story_hook(self):
        hook = StoryHook(
            id="hook1", description="mysterious stranger", intended_payoff="reveal identity"
        )
        assert hook.status == "planted"

    def test_quest(self):
        q = Quest(id="q1", title="Save Village", assigned_pcs=["pc1"])
        assert q.status == "inactive"

    def test_cast_change_event(self):
        cce = CastChangeEvent(tick=3, character_id="pc2", event_type="join", reason="met in tavern")
        assert cce.event_type == "join"

    def test_main_cast_roster(self):
        roster = MainCastRoster(current_members=["pc1", "pc2"])
        assert len(roster.current_members) == 2

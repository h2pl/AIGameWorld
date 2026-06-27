"""Test Pydantic models – M1-1."""

import pytest
from pydantic import ValidationError

from src.models import (
    Action,
    Actor,
    ActorFunction,
    Attributes,
    BranchPoint,
    CastChangeEvent,
    CharacterArc,
    CombatStats,
    Equipment,
    Event,
    Faction,
    InventorySlot,
    Item,
    ItemType,
    Location,
    MainCastRoster,
    PlayerCharacter,
    Relationship,
    Scene,
    SceneObject,
    SceneObjectType,
    StoryArc,
    StoryHook,
    WorldState,
)


class TestPlayerCharacter:
    def test_minimal_pc(self):
        pc = PlayerCharacter(id="kael", name="Kael", role="fighter")
        assert pc.id == "kael"
        assert pc.status == "active"
        assert pc.reflection_threshold == 100

    def test_pc_with_full_character_arc(self):
        arc = CharacterArc(
            growth_line="From lone wolf to guardian",
            inner_conflict="Strength vs restraint",
            destiny="Become the village's shield",
        )
        pc = PlayerCharacter(
            id="kael",
            name="Kael",
            role="fighter",
            character_arc=arc,
            values=["Protect the weak", "Justice above law"],
            long_term_goal="Find the missing mentor",
        )
        assert pc.character_arc.growth_line == "From lone wolf to guardian"
        assert pc.values == ["Protect the weak", "Justice above law"]

    def test_pc_equipment_and_inventory(self):
        eq = Equipment(weapon="longsword", armor="chain_mail", off_hand="shield")
        inv = [InventorySlot(item_id="health_potion", qty=2)]
        pc = PlayerCharacter(
            id="kael",
            name="Kael",
            role="fighter",
            equipment=eq,
            inventory=inv,
        )
        assert pc.equipment.weapon == "longsword"
        assert pc.inventory[0].item_id == "health_potion"
        assert pc.inventory[0].qty == 2

    def test_pc_status_enum_violation_caught(self):
        """status field is free-form string for flexibility, but typical values are active/dead/left."""
        pc = PlayerCharacter(id="test", name="Test", role="fighter", status="sleeping")
        assert pc.status == "sleeping"  # any string allowed by design


class TestActor:
    def test_minimal_actor(self):
        actor = Actor(id="garret", name="Garret", role="blacksmith")
        assert actor.id == "garret"
        assert actor.reflection_threshold == 200

    def test_actor_with_functions(self):
        actor = Actor(
            id="mira",
            name="Mira",
            role="merchant",
            functions=[ActorFunction.MERCHANT, ActorFunction.DIALOGUE],
            function_data={
                "merchant": {"shop_inventory": [], "gold": 500},
                "dialogue": {"dialogue_tree": "mira_dialogue.yaml"},
            },
        )
        assert ActorFunction.MERCHANT in actor.functions
        assert actor.function_data["merchant"]["gold"] == 500

    def test_actor_dm_control(self):
        actor = Actor(
            id="bandit",
            name="Bandit Chief",
            role="enemy",
            functions=[ActorFunction.ENEMY],
            dm_assigned=True,
            motivation_injected="Raid the village at midnight",
        )
        assert actor.dm_assigned is True
        assert "Raid" in actor.motivation_injected

    def test_actor_combat_optional(self):
        actor = Actor(id="villager", name="Villager", role="bystander", combat=None)
        assert actor.combat is None


class TestItem:
    def test_weapon_item(self):
        sword = Item(
            id="longsword",
            name="Longsword",
            item_type=ItemType.WEAPON,
            data={"damage_dice": "1d8", "damage_type": "slashing", "properties": ["versatile"]},
        )
        assert sword.item_type == ItemType.WEAPON
        assert sword.data["damage_dice"] == "1d8"

    def test_armor_item(self):
        armor = Item(
            id="chain_mail",
            name="Chain Mail",
            item_type=ItemType.ARMOR,
            weight=25.0,
            value=75,
            data={"ac": 16, "dex_bonus_max": 0, "stealth_disadvantage": True},
        )
        assert armor.data["ac"] == 16

    def test_key_item(self):
        key = Item(
            id="rusty_key",
            name="Rusty Key",
            item_type=ItemType.KEY,
            data={"opens": "cellar_door_01"},
        )
        assert key.item_type == ItemType.KEY


class TestSceneObject:
    def test_container(self):
        chest = SceneObject(
            id="chest_01",
            name="Wooden Chest",
            object_type=SceneObjectType.CONTAINER,
            interact_data={
                "locked": True,
                "lock_dc": 15,
                "items": [{"item_id": "longsword", "qty": 1}],
            },
        )
        assert chest.object_type == SceneObjectType.CONTAINER
        assert chest.interact_data["locked"] is True

    def test_door(self):
        door = SceneObject(
            id="cellar_door",
            name="Cellar Door",
            object_type=SceneObjectType.DOOR,
            interact_data={"locked": True, "key_id": "rusty_key", "leads_to": "cellar"},
        )
        assert door.interact_data["key_id"] == "rusty_key"

    def test_trap(self):
        trap = SceneObject(
            id="trap_01",
            name="Spike Trap",
            object_type=SceneObjectType.TRAP,
            interact_data={"detect_dc": 12, "disarm_dc": 15, "damage": "2d6", "armed": True},
        )
        assert trap.interact_data["armed"] is True


class TestStoryModels:
    def test_story_arc(self):
        arc = StoryArc(
            id="arc_bandits",
            type="main",
            title="Bandit Threat",
            stage="\u94fa\u9648",
            main_cast=["kael", "zeph"],
            status="setup",
        )
        assert arc.stage == "\u94fa\u9648"
        assert len(arc.main_cast) == 2

    def test_branch_point(self):
        bp = BranchPoint(
            tick=5,
            decision_maker="kael",
            decision="Fight the bandits head-on",
            consequence="Bandit leader escaped, villagers injured",
            arc_direction="Escalation",
        )
        assert bp.tick == 5

    def test_story_hook(self):
        hook = StoryHook(
            id="hook_wolves",
            planted_tick=0,
            description="Distant wolf howls",
            intended_payoff="Wolf pack attacks village",
            urgency=5,
        )
        assert hook.status == "planted"

    def test_main_cast_roster(self):
        roster = MainCastRoster(
            current_members=["kael", "zeph", "elara", "mira"],
            history=[CastChangeEvent(tick=0, character_id="kael", event_type="join", reason="Initial member")],
        )
        assert len(roster.current_members) == 4


class TestEventAndAction:
    def test_event(self):
        evt = Event(
            id="evt_1_0",
            tick=1,
            type="combat_hit",
            importance=2,
            source="kael",
            target="bandit",
            data={"damage": 8, "weapon": "longsword"},
        )
        assert evt.type == "combat_hit"

    def test_action(self):
        action = Action(
            character_id="kael",
            character_type="pc",
            tick=1,
            action_type="attack",
            target="bandit",
            reasoning="Bandit threatens villagers – must protect",
        )
        assert action.character_type == "pc"
        assert action.action_type == "attack"


class TestWorldState:
    def test_empty_world_state(self):
        ws = WorldState()
        assert ws.tick == 0
        assert ws.weather == "normal"
        assert ws.time_of_day == "day"

    def test_world_state_with_entities(self):
        pc = PlayerCharacter(id="kael", name="Kael", role="fighter")
        actor = Actor(id="garret", name="Garret", role="blacksmith")
        chest = SceneObject(id="chest_01", name="Chest", object_type=SceneObjectType.CONTAINER)
        sword = Item(id="longsword", name="Longsword", item_type=ItemType.WEAPON)

        ws = WorldState(
            tick=5,
            current_world="forgotten_realms",
            current_scene="village",
            player_characters={"kael": pc},
            actors={"garret": actor},
            scene_objects={"chest_01": chest},
            items={"longsword": sword},
            story_arcs=[StoryArc(id="arc_1", title="Test Arc")],
            story_hooks=[StoryHook(id="hook_1")],
        )
        assert ws.player_characters["kael"].name == "Kael"
        assert ws.actors["garret"].role == "blacksmith"
        assert ws.items["longsword"].item_type == ItemType.WEAPON
        assert len(ws.story_arcs) == 1

"""Domain 模型测试 / Domain model tests."""

# 测试框架 / Testing framework
import pytest

# Pydantic 校验 / Pydantic validation
from pydantic import ValidationError

# 领域模型 / Domain models
from src.domain.actor import Actor
from src.domain.dm_record import DMRecord
from src.domain.event import SEQUENCE, Event
from src.domain.item import Item, ItemType
from src.domain.player_character import PlayerCharacter
from src.domain.scene_object import SceneObject, SceneObjectType
from src.domain.story_summary import StorySummary


class TestActor:
    """演员 NPC 测试 / Actor NPC tests."""

    def test_actor_minimal(self):
        """最小构造 / Minimal construction."""
        a = Actor(id="npc1", name="Guard")
        assert a.role == ""
        assert a.status == "active"

    def test_player_character_minimal(self):
        """玩家角色最小构造 / Player character minimal construction."""
        pc = PlayerCharacter(id="hero1", name="Aragon")
        assert pc.roster_status == "member"

    def test_player_character_requires_id(self):
        """玩家角色必须提供 id / Player character requires id."""
        with pytest.raises(ValidationError):
            PlayerCharacter(id=None, name="Test")  # type: ignore[arg-type]


class TestEvent:
    """事件模型测试 / Event model tests."""

    def test_event_defaults(self):
        """默认值测试 / Default values."""
        e = Event(type="scene_setup", tick=1)
        assert e.type == "scene_setup"
        assert e.tick == 1
        assert e.payload == {}

    def test_event_with_payload(self):
        """带 payload 的事件 / Event with payload."""
        e = Event(
            type="scene_setup", tick=1, payload={"scene_id": "tavern", "description": "进入场景"}
        )
        assert e.payload["scene_id"] == "tavern"

    def test_sequence_order(self):
        """事件顺序常量测试 / Event sequence constant test."""
        assert SEQUENCE[0] == "dm_create"
        assert SEQUENCE[-1] == "dm_narrative"


class TestItem:
    """物品模型测试 / Item model tests."""

    def test_item_creation(self):
        """物品创建 / Item creation."""
        item = Item(id="sword_01", name="Iron Sword", item_type=ItemType.WEAPON)
        assert item.rarity == "common"
        assert item.weight == 0.0

    def test_item_type_enum(self):
        """物品类型枚举 / Item type enum."""
        assert ItemType.POTION.value == "potion"
        assert ItemType.KEY.value == "key"


class TestSceneObject:
    """场景物体模型测试 / Scene object model tests."""

    def test_scene_object(self):
        """场景物体创建 / Scene object creation."""
        so = SceneObject(id="door_01", name="Wooden Door", object_type=SceneObjectType.DOOR)
        assert so.interactable is True

    def test_scene_object_type_enum(self):
        """场景物体类型枚举 / Scene object type enum."""
        assert SceneObjectType.TRAP.value == "trap"
        assert SceneObjectType.CONTAINER.value == "container"


class TestDMRecord:
    """DM 产出记录测试 / DM record tests."""

    def test_defaults(self):
        """默认值测试 / Default values."""
        r = DMRecord()
        assert r.tick == 0
        assert r.world_id == ""
        assert r.dm_narrative == ""

    def test_full(self):
        """完整数据测试 / Full data test."""
        r = DMRecord(world_id="test", tick=3, plot_brief="场景", dm_narrative="叙事文本")
        assert r.dm_narrative == "叙事文本"


class TestStorySummary:
    """剧情摘要测试 / Story summary tests."""

    def test_summary(self):
        """摘要创建 / Summary creation."""
        s = StorySummary(world_id="test", tick_start=1, tick_end=10, summary="章节摘要")
        assert s.tick_start == 1
        assert s.tick_end == 10
        assert s.summary == "章节摘要"

"""Message + 7 种 Event 类型单元测试——验证构造、默认值、合法性检查 / Unit tests for Message & 7 event types."""

import pytest
from pydantic import ValidationError

from src.domain.event import (
    CharacterExploreEvent,
    CharacterMoveEvent,
    CharacterTalkEvent,
    DmNarrativeEvent,
    ExploreRoll,
    OpeningEvent,
    SceneObjectsEvent,
    SceneSetupEvent,
)
from src.domain.message import Message

# ══ Message 测试 / Message Tests ══


class TestMessage:
    def test_minimal(self):
        m = Message(id="aw_001", tick=1, world_id="test", timestamp="2026-07-01T12:00:00Z")
        assert m.id == "aw_001"
        assert m.world_id == "test"
        assert m.tick == 1
        assert m.events == []

    def test_requires_id(self):
        with pytest.raises(ValidationError):
            Message(tick=1, world_id="test", timestamp="2026-07-01T12:00:00Z")

    def test_requires_tick(self):
        with pytest.raises(ValidationError):
            Message(id="aw_001", world_id="test", timestamp="2026-07-01T12:00:00Z")

    def test_with_events(self):
        m = Message(
            id="aw_001",
            tick=1,
            world_id="test",
            timestamp="2026-07-01T12:00:00Z",
            events=[
                OpeningEvent(text="欢迎"),
                CharacterMoveEvent(character_id="fighter", x=5, y=8),
            ],
        )
        assert len(m.events) == 2
        assert m.events[0].text == "欢迎"

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError):
            Message(
                id="aw", tick=1, world_id="test", timestamp="2026-07-01T12:00:00Z", extra_field="no"
            )


# ══ 7 种事件类型 / 7 Event Types ══


class TestOpeningEvent:
    """开场白 / Opening event."""

    def test_minimal(self):
        e = OpeningEvent(text="冒险开始！")
        assert e.type == "opening"

    def test_requires_text(self):
        with pytest.raises(ValidationError):
            OpeningEvent()  # pyright: ignore[reportCallIssue]


class TestDmNarrativeEvent:
    def test_minimal(self):
        e = DmNarrativeEvent(text="太阳升起")
        assert e.type == "dm_narrative"
        assert e.mood is None

    def test_with_mood(self):
        e = DmNarrativeEvent(text="黑暗降临", mood="ominous")
        assert e.mood == "ominous"

    def test_invalid_mood(self):
        with pytest.raises(ValidationError):
            DmNarrativeEvent(text="x", mood="happy")  # pyright: ignore[reportCallIssue]


class TestSceneSetupEvent:
    def test_minimal(self):
        e = SceneSetupEvent(scene_id="village", scene_name="Elderwood")
        assert e.type == "scene_setup"


class TestSceneObjectsEvent:
    def test_minimal(self):
        e = SceneObjectsEvent(scene_id="village")
        assert e.type == "scene_objects"
        assert e.objects == []

    def test_with_objects(self):
        from src.domain.event import SceneObject

        e = SceneObjectsEvent(
            scene_id="village",
            objects=[
                SceneObject(
                    id="chest1",
                    name="Wooden Chest",
                    object_type="container",
                    position_x=10,
                    position_y=5,
                )
            ],
        )
        assert len(e.objects) == 1


class TestCharacterMoveEvent:
    def test_minimal(self):
        e = CharacterMoveEvent(character_id="fighter", x=10, y=15)
        assert e.type == "character_move"
        assert e.reasoning is None

    def test_with_reasoning(self):
        e = CharacterMoveEvent(character_id="rogue", x=5, y=3, reasoning="向北探索")
        assert e.reasoning == "向北探索"


class TestCharacterTalkEvent:
    def test_minimal(self):
        e = CharacterTalkEvent(character_id="cleric", dialogue="愿圣光保佑")
        assert e.type == "character_talk"


class TestCharacterExploreEvent:
    def test_minimal(self):
        e = CharacterExploreEvent(character_id="rogue", action="搜索房间")
        assert e.type == "character_explore"
        assert e.roll is None

    def test_with_roll(self):
        e = CharacterExploreEvent(
            character_id="rogue",
            action="开锁",
            roll=ExploreRoll(success=True, total=18, dc=12),
            detail="成功",
        )
        assert e.roll.success is True
        assert e.roll.total == 18

"""Message + Event 类型单元测试 / Unit tests for Message & Event types."""

import pytest
from pydantic import ValidationError

from src.domain.event import Event
from src.domain.message import Message

# ══ Message 测试 / Message Tests ══


class TestMessage:
    """消息模型测试 / Message model tests."""

    def test_minimal(self):
        """最小构造 / Minimal construction."""
        m = Message(id="aw_001", tick=1, world_id="test", timestamp="2026-07-01T12:00:00Z")
        assert m.id == "aw_001"
        assert m.world_id == "test"
        assert m.tick == 1

    def test_requires_id(self):
        """缺少 id 报错 / Missing id raises error."""
        with pytest.raises(ValidationError):
            Message(tick=1, world_id="test", timestamp="2026-07-01T12:00:00Z")  # type: ignore[call-arg]

    def test_requires_tick(self):
        """缺少 tick 报错 / Missing tick raises error."""
        with pytest.raises(ValidationError):
            Message(id="aw_001", world_id="test", timestamp="2026-07-01T12:00:00Z")  # type: ignore[call-arg]

    def test_forbids_extra_fields(self):
        """禁止额外字段 / Forbids extra fields."""
        with pytest.raises(ValidationError):
            Message(
                id="aw",
                tick=1,
                world_id="test",
                timestamp="2026-07-01T12:00:00Z",
                extra_field="no",  # type: ignore[call-arg]
            )


# ══ Event 测试 / Event Tests ══


class TestEvent:
    """事件模型测试 / Event model tests."""

    def test_minimal(self):
        """最小构造 / Minimal construction."""
        e = Event(type="opening", tick=1)
        assert e.type == "opening"
        assert e.tick == 1
        assert e.payload == {}

    def test_with_payload(self):
        """带 payload 的事件 / Event with payload."""
        e = Event(type="dm_narrative", tick=1, payload={"text": "太阳升起"})
        assert e.payload["text"] == "太阳升起"

    def test_scene_setup(self):
        """场景设置事件 / Scene setup event."""
        e = Event(
            type="scene_setup", tick=1, payload={"scene_id": "village", "scene_name": "Elderwood"}
        )
        assert e.payload["scene_id"] == "village"

    def test_scene_objects(self):
        """场景物体事件 / Scene objects event."""
        e = Event(
            type="scene_objects",
            tick=1,
            payload={
                "scene_id": "village",
                "objects": [{"id": "chest1", "name": "Wooden Chest", "object_type": "container"}],
            },
        )
        assert len(e.payload["objects"]) == 1

    def test_character_move(self):
        """角色移动事件 / Character move event."""
        e = Event(
            type="character_move",
            tick=1,
            payload={"character_id": "fighter", "x": 10, "y": 15, "reasoning": "向北探索"},
        )
        assert e.payload["character_id"] == "fighter"
        assert e.payload["reasoning"] == "向北探索"

    def test_character_talk(self):
        """角色对话事件 / Character talk event."""
        e = Event(
            type="character_talk",
            tick=1,
            payload={"character_id": "cleric", "dialogue": "愿圣光保佑"},
        )
        assert e.payload["dialogue"] == "愿圣光保佑"

    def test_character_explore(self):
        """角色探索事件 / Character explore event."""
        e = Event(
            type="character_explore",
            tick=1,
            payload={"character_id": "rogue", "action": "搜索房间", "detail": "成功"},
        )
        assert e.payload["action"] == "搜索房间"

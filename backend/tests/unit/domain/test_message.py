"""Message + Event 类型单元测试 / Unit tests for Message & Event types."""

import pytest
from pydantic import ValidationError

from src.domain.event import TickEvent, TickEventType
from src.domain.message import TickMessage

# ══ Message 测试 / Message Tests ══


class TestMessage:
    """消息模型测试 / Message model tests."""

    def test_minimal(self):
        """最小构造 / Minimal construction."""
        m = TickMessage(id="aw_001", tick=1, world_id="test")
        assert m.id == "aw_001"
        assert m.world_id == "test"
        assert m.tick == 1
        assert m.status == "building"
        assert m.is_last is False

    def test_requires_id(self):
        """缺少 id 报错 / Missing id raises error."""
        with pytest.raises(ValidationError):
            TickMessage(tick=1, world_id="test")  # type: ignore[call-arg]

    def test_requires_tick(self):
        """缺少 tick 报错 / Missing tick raises error."""
        with pytest.raises(ValidationError):
            TickMessage(id="aw_001", world_id="test")  # type: ignore[call-arg]

    def test_forbids_extra_fields(self):
        """禁止额外字段 / Forbids extra fields."""
        with pytest.raises(ValidationError):
            TickMessage(
                id="aw",
                tick=1,
                world_id="test",
                extra_field="no",  # type: ignore[call-arg]
            )


# ══ Event 测试 / Event Tests ══


class TestEvent:
    """事件模型测试 / Event model tests."""

    def test_minimal(self):
        """最小构造 / Minimal construction."""
        e = TickEvent(type=TickEventType.DM_CREATE, tick=1)
        assert e.type == TickEventType.DM_CREATE
        assert e.tick == 1
        assert e.payload == {}

    def test_with_payload(self):
        """带 payload 的事件 / Event with payload."""
        e = TickEvent(type=TickEventType.DM_CREATE, tick=1, payload={"scene_id": "tavern"})
        assert e.payload["scene_id"] == "tavern"

    def test_all_types(self):
        """所有事件类型可构造 / All event types constructible."""
        for et in TickEventType:
            e = TickEvent(type=et, tick=1)
            assert e.type == et

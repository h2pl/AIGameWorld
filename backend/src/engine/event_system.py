"""Event 系统: 队列/分发/日志 / Event system: queue/dispatch/log."""

from typing import Any
from collections import deque


class EventSystem:
    """事件队列与分发 / Event queue and dispatch.
    
    职责 / Responsibilities:
    - 维护事件队列 / Maintain event queue
    - 按类型过滤事件 / Filter events by type
    - 持久化事件到 SQLite（通过 WorldStateStore）/ Persist to SQLite via WorldStateStore
    """

    def __init__(self):
        self._queue: deque[dict[str, Any]] = deque()  # 事件队列 / Event queue

    def push(self, event: dict[str, Any]) -> None:
        """添加事件 / Push an event."""
        self._queue.append(event)

    def push_batch(self, events: list[dict[str, Any]]) -> None:
        """批量添加事件 / Push multiple events."""
        self._queue.extend(events)

    def pop_all(self) -> list[dict[str, Any]]:
        """取出全部事件并清空 / Pop all events and clear."""
        result = list(self._queue)
        self._queue.clear()
        return result

    def filter_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """按类型过滤事件 / Filter events by type."""
        return [e for e in self._queue if e.get("type") == event_type]

    def latest_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取最近 N 条事件 / Get latest N events."""
        items = list(self._queue)
        return items[-limit:] if len(items) > limit else items

    @property
    def pending_count(self) -> int:
        """待处理事件数 / Pending event count."""
        return len(self._queue)

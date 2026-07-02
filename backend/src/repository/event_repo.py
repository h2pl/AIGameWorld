"""Event 仓储 / Event Repository——写入 + 按tick范围加载."""

import json
import logging

from ..domain.event import TICK_EVENT_SEQUENCE, TickEvent
from ..storage.sqlite_client import SQLiteClient

logger = logging.getLogger("aw.repo.event")


class TickEventRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def insert_tick_events(
        self, tick_message_id: str, msg_tick: int, tick_events: list[dict | TickEvent]
    ) -> None:
        """批量写入事件."""
        for ev in tick_events:
            if isinstance(ev, TickEvent):
                ev_type = ev.type
                ev_payload = ev.payload
            else:
                ev_type = ev["type"]
                ev_payload = ev.get("payload", ev)
            await self._db.execute(
                "INSERT INTO tick_events (tick_message_id, msg_tick, type, payload) VALUES (?, ?, ?, ?)",
                (tick_message_id, msg_tick, ev_type, json.dumps(ev_payload, default=str)),
            )
        await self._db.commit()
        logger.info(
            "[event] insert %s tick=%s count=%d", tick_message_id, msg_tick, len(tick_events)
        )

    async def insert_events(
        self, tick_message_id: str, msg_tick: int, events: list[dict | TickEvent]
    ) -> None:
        """兼容旧接口 / Legacy alias."""
        await self.insert_tick_events(tick_message_id, msg_tick, events)

    async def load_by_tick_range(self, world_id: str, tick_start: int, tick_end: int) -> list[dict]:
        """按 world_id + tick 范围加载事件."""
        rows = await self._db.fetch_all(
            "SELECT e.type, e.payload, m.tick FROM tick_events e "
            "JOIN tick_messages m ON e.tick_message_id = m.id AND e.msg_tick = m.tick "
            "WHERE m.world_id = ? AND m.tick BETWEEN ? AND ? ORDER BY m.tick, e.id",
            (world_id, tick_start, tick_end),
        )
        return [{"tick": r["tick"], "type": r["type"], "payload": r["payload"]} for r in rows]

    async def load_by_message(self, tick_message_id: str, msg_tick: int) -> list[TickEvent]:
        """按消息加载事件."""
        rows = await self._db.fetch_all(
            "SELECT id, type, payload FROM tick_events WHERE tick_message_id = ? AND msg_tick = ? ORDER BY id",
            (tick_message_id, msg_tick),
        )
        result: list[TickEvent] = []
        for r in rows:
            payload = json.loads(r["payload"])
            if not isinstance(payload, dict):
                payload = {"description": payload}
            result.append(TickEvent(type=r["type"], tick=msg_tick, payload=payload))
        order_index = {event_type: index for index, event_type in enumerate(TICK_EVENT_SEQUENCE)}
        return sorted(result, key=lambda ev: order_index.get(ev.type, len(TICK_EVENT_SEQUENCE)))


EventRepo = TickEventRepo

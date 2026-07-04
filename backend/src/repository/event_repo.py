"""Event 仓储 / Event Repository——写入 + 按tick范围加载."""

import json

from ..domain.event import TICK_EVENT_SEQUENCE, TickEvent, TickEventType
from ..storage.sqlite_client import SQLiteClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


class TickEventRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def insert_tick_events(
        self,
        tick_message_id: str,
        tick: int,
        tick_events: list[dict | TickEvent],
        world_id: str = "",
    ) -> None:
        """批量写入事件."""
        for ev in tick_events:
            if isinstance(ev, TickEvent):
                ev_type = ev.type
                ev_payload = ev.payload
                ev_world = ev.world_id or world_id
            else:
                ev_type = ev["type"]
                ev_payload = ev.get("payload", ev)
                ev_world = ev.get("world_id", world_id)
            await self._db.execute(
                "INSERT INTO tick_events (tick_message_id, tick, type, payload, world_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (tick_message_id, tick, ev_type, json.dumps(ev_payload, default=str), ev_world),
            )
        await self._db.commit()
        logger.info("[repo] insert %s tick=%s count=%d", tick_message_id, tick, len(tick_events))

    async def insert_events(
        self,
        tick_message_id: str,
        tick: int,
        events: list[dict | TickEvent],
        world_id: str = "",
    ) -> None:
        """兼容旧接口 / Legacy alias."""
        await self.insert_tick_events(tick_message_id, tick, events, world_id)

    async def load_by_tick_range(self, world_id: str, tick_start: int, tick_end: int) -> list[dict]:
        """按 world_id + tick 范围加载事件（直接用 tick_events.world_id）."""
        rows = await self._db.fetch_all(
            "SELECT type, payload, tick FROM tick_events "
            "WHERE world_id = ? AND tick BETWEEN ? AND ? ORDER BY tick, id",
            (world_id, tick_start, tick_end),
        )
        return [
            {"tick": r["tick"], "type": r["type"], "payload": json.loads(r["payload"])}
            for r in rows
        ]

    async def load_by_message(self, tick_message_id: str, tick: int) -> list[TickEvent]:
        """按消息加载事件."""
        rows = await self._db.fetch_all(
            "SELECT id, type, payload FROM tick_events WHERE tick_message_id = ? AND tick = ? ORDER BY id",
            (tick_message_id, tick),
        )
        result: list[TickEvent] = []
        for r in rows:
            payload = json.loads(r["payload"])
            if not isinstance(payload, dict):
                payload = {"description": payload}
            result.append(TickEvent(type=TickEventType(r["type"]), tick=tick, payload=payload))
        order_index = {event_type: index for index, event_type in enumerate(TICK_EVENT_SEQUENCE)}
        return sorted(result, key=lambda ev: order_index.get(ev.type, len(TICK_EVENT_SEQUENCE)))

    async def delete_by_world(self, world_id: str) -> int:
        """删除指定 world 的全部事件，返回删除行数 / Delete all events for a world."""
        await self._db.execute("DELETE FROM tick_events WHERE world_id = ?", (world_id,))
        await self._db.commit()
        logger.info("[repo] deleted events for world=%s", world_id)
        return 0


EventRepo = TickEventRepo

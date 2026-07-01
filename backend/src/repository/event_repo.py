"""写入 event + 按 msg 加载."""

import json

from pydantic import TypeAdapter

from ..domain.event import SEQUENCE, Event
from ..storage.sqlite_client import SQLiteClient

_event_adapter = TypeAdapter(Event)
_type_order = {t: i for i, t in enumerate(SEQUENCE)}


class EventRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def insert_batch(self, msg_id: str, msg_tick: int, events: list[Event]) -> None:
        """逐条写入，id 自增 = 入库顺序."""
        for ev in events:
            ev_dict = ev.model_dump()
            ev_type = ev_dict.pop("type")
            await self._db.execute(
                "INSERT INTO events (msg_id, msg_tick, type, payload) VALUES (?, ?, ?, ?)",
                (msg_id, msg_tick, ev_type, json.dumps(ev_dict, default=str)),
            )
        await self._db.commit()

    async def load_by_message(self, msg_id: str, msg_tick: int) -> list[Event]:
        """按 (msg_id, msg_tick) 加载，按 SEQUENCE 排序，同类按 id（入库顺序）."""
        rows = await self._db.fetch_all(
            "SELECT type, payload FROM events WHERE msg_id = ? AND msg_tick = ? ORDER BY id",
            (msg_id, msg_tick),
        )
        events: list[Event] = []
        for r in rows:
            data = json.loads(r["payload"])
            data["type"] = r["type"]
            events.append(_event_adapter.validate_python(data))
        events.sort(key=lambda ev: _type_order.get(ev.model_dump()["type"], 99))
        return events

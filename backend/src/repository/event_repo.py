"""事件仓储."""

import json

from ..domain import Event
from ..storage.sqlite_client import SQLiteClient


class EventRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def insert(self, evt: Event) -> None:
        await self._db.execute(
            "INSERT INTO events (id, tick, seq, type, importance, source, target, data_json, narrative) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evt.id,
                evt.tick,
                evt.seq,
                evt.type,
                evt.importance,
                evt.source,
                evt.target,
                json.dumps(evt.data),
                evt.narrative,
            ),
        )

    async def load_all(self) -> list[Event]:
        rows = await self._db.fetch_all("SELECT * FROM events ORDER BY tick, seq")
        return [
            Event(
                id=r["id"],
                tick=r["tick"],
                seq=r["seq"],
                type=r["type"],
                importance=r["importance"],
                source=r["source"],
                target=r.get("target"),
                data=json.loads(r["data_json"]),
                narrative=r.get("narrative"),
            )
            for r in rows
        ]

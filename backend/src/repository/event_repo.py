"""Event 仓储 / Event Repository——写入 + 按tick范围加载."""

import json

from pydantic import BaseModel

from ..domain.event import TickEvent
from ..storage.sqlite_client import SQLiteClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _json_default(obj):
    """序列化嵌套 Pydantic 模型 / Serialize nested Pydantic models."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    return str(obj)


class TickEventRepo:
    def __init__(self, client: SQLiteClient):
        self._db = client

    async def insert_tick_events(
        self,
        tick: int,
        tick_events: list[dict | TickEvent],
        world_id: str = "",
    ) -> None:
        """批量写入事件 / Batch insert events."""
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
                "INSERT INTO tick_events (tick, type, payload, world_id, updated_at) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
                (
                    tick,
                    ev_type,
                    json.dumps(ev_payload, ensure_ascii=False, default=_json_default),
                    ev_world,
                ),
            )
        await self._db.commit()
        logger.info("[repo] insert tick=%s count=%d", tick, len(tick_events))

    async def load_by_tick_range(self, world_id: str, tick_start: int, tick_end: int) -> list[dict]:
        """按 world_id + tick 范围加载事件."""
        rows = await self._db.fetch_all(
            "SELECT type, payload, tick FROM tick_events "
            "WHERE world_id = ? AND tick BETWEEN ? AND ? ORDER BY tick, id",
            (world_id, tick_start, tick_end),
        )
        return [
            {"tick": r["tick"], "type": r["type"], "payload": json.loads(r["payload"])}
            for r in rows
        ]

    async def delete_by_world(self, world_id: str) -> int:
        """删除指定 world 的全部事件."""
        await self._db.execute("DELETE FROM tick_events WHERE world_id = ?", (world_id,))
        await self._db.commit()
        logger.info("[repo] deleted events for world=%s", world_id)
        return 0


EventRepo = TickEventRepo

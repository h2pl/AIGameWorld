"""消息仓储——tick_messages 表 CRUD / Message repository: insert / get pending / ack."""

import logging

from ..domain.message import TickMessage
from ..storage.sqlite_client import SQLiteClient
from ..utils.logging import log_msg

logger = logging.getLogger("aw.repo.msg")


class TickMessageRepo:
    """消息持久化 / Message persistence."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    async def insert(self, msg: TickMessage) -> None:
        """写入一条消息 / Insert a message."""
        await self._db.execute(
            "INSERT INTO tick_messages (id, tick, world_id) VALUES (?, ?, ?)",
            (msg.id, msg.tick, msg.world_id),
        )
        await self._db.commit()
        log_msg("insert", msg.id, msg.tick, event_count=len(msg.tick_events))

    async def get_next_pending(self, mid: str) -> dict | None:
        """读取下一条 pending 消息 / Fetch next pending message."""
        row = await self._db.fetch_one(
            "SELECT id, tick, world_id, status, created_at FROM tick_messages "
            "WHERE id = ? AND status = 'pending' "
            "ORDER BY tick LIMIT 1",
            (mid,),
        )
        if row:
            log_msg("next_pending", mid, row["tick"])
        return row

    async def mark_ready(self, mid: str, tick: int) -> None:
        """事件落盘后标记消息为可消费 / Mark a message consumable once its events are persisted."""
        await self._db.execute(
            "UPDATE tick_messages SET status = 'pending', updated_at = datetime('now') "
            "WHERE id = ? AND tick = ?",
            (mid, tick),
        )
        await self._db.commit()
        log_msg("ready", mid, tick)

    async def ack(self, mid: str, tick: int) -> None:
        """标记已消费 / Mark as consumed."""
        await self._db.execute(
            "UPDATE tick_messages SET status = 'consumed', acked_at = datetime('now'), "
            "updated_at = datetime('now') "
            "WHERE id = ? AND tick = ?",
            (mid, tick),
        )
        await self._db.commit()


MessageRepo = TickMessageRepo

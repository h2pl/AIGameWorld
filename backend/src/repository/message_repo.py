"""消息仓储——messages 表 CRUD / Message repository: insert / get pending / ack."""

from ..domain.message import Message
from ..storage.sqlite_client import SQLiteClient


class MessageRepo:
    """消息持久化 / Message persistence."""

    def __init__(self, client: SQLiteClient):
        self._db = client

    async def insert(self, msg: Message) -> None:
        """写入一条消息 / Insert a message."""
        await self._db.execute(
            "INSERT INTO messages (id, tick, world_id) VALUES (?, ?, ?)",
            (msg.id, msg.tick, msg.world_id),
        )
        await self._db.commit()

    async def get_next_pending(self, mid: str) -> dict | None:
        """读取下一条 pending 消息 / Fetch next pending message."""
        return await self._db.fetch_one(
            "SELECT id, tick, world_id, status, created_at FROM messages "
            "WHERE id = ? AND status = 'pending' "
            "ORDER BY tick LIMIT 1",
            (mid,),
        )

    async def ack(self, mid: str, tick: int) -> None:
        """标记已消费 / Mark as consumed."""
        await self._db.execute(
            "UPDATE messages SET status = 'consumed', acked_at = datetime('now'), "
            "updated_at = datetime('now') "
            "WHERE id = ? AND tick = ?",
            (mid, tick),
        )
        await self._db.commit()

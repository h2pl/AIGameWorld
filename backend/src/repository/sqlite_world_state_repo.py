"""SQLite 实现 WorldStateRepo — 用 storage/sqlite_client 做裸 DB 操作，自身只做领域读写。"""

import json
from typing import Any

from ..storage.sqlite_client import SQLiteClient
from .world_state_repo import WorldStateRepo


class SQLiteWorldStateRepo(WorldStateRepo):
    """领域层：tick 状态存取。不写 SQL，调 SQLiteClient."""

    def __init__(self, client: SQLiteClient | None = None):
        self._client = client or SQLiteClient()

    async def init(self) -> None:
        await self._client.execute("""
            CREATE TABLE IF NOT EXISTS tick_states (
                tick INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    async def save(self, state: dict[str, Any], tick: int) -> None:
        await self._client.execute(
            "INSERT OR REPLACE INTO tick_states (tick, state_json) VALUES (?, ?)",
            tick, json.dumps(state, default=str),
        )

    async def load(self, tick: int) -> dict[str, Any] | None:
        row = await self._client.fetch_one(
            "SELECT state_json FROM tick_states WHERE tick = ?", tick,
        )
        return json.loads(row[0]) if row else None

    async def load_latest(self) -> dict[str, Any] | None:
        row = await self._client.fetch_one(
            "SELECT tick, state_json FROM tick_states ORDER BY tick DESC LIMIT 1",
        )
        return {**json.loads(row[1]), "tick": row[0]} if row else None

    async def rollback(self, tick: int) -> None:
        await self._client.execute("DELETE FROM tick_states WHERE tick > ?", tick)

    async def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = await self._client.fetch_all(
            "SELECT tick, state_json FROM tick_states ORDER BY tick DESC LIMIT ?", limit,
        )
        return [{**json.loads(r[1]), "tick": r[0]} for r in rows]

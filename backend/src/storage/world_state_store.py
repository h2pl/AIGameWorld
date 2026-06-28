"""SQLite WorldStateStore — 实现 WorldStateRepo 接口."""

import json
from typing import Any

import aiosqlite

from ..repository.world_state_repo import WorldStateRepo


class SQLiteWorldStateStore(WorldStateRepo):
    """SQLite 实现 World State 持久化."""

    def __init__(self, db_path: str = "data/world_state.db"):
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tick_states (
                    tick INTEGER PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def save(self, state: dict[str, Any], tick: int) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO tick_states (tick, state_json) VALUES (?, ?)",
                (tick, json.dumps(state, default=str)),
            )
            await db.commit()

    async def load(self, tick: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT state_json FROM tick_states WHERE tick = ?", (tick,)
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else None

    async def load_latest(self) -> dict[str, Any] | None:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT tick, state_json FROM tick_states ORDER BY tick DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                return {**json.loads(row[1]), "tick": row[0]} if row else None

    async def rollback(self, tick: int) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM tick_states WHERE tick > ?", (tick,))
            await db.commit()

    async def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT tick, state_json FROM tick_states ORDER BY tick DESC LIMIT ?",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [{**json.loads(r[1]), "tick": r[0]} for r in rows]

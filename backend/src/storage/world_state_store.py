"""WorldStateStore：SQLite 持久化 / SQLite persistence.

每个 tick 的 OverallState 存为 JSON blob，支持回退和恢复。
"""

import json
from typing import Any

import aiosqlite


class WorldStateStore:
    """World State 存储层——tick 级别的增/查/回退."""

    def __init__(self, db_path: str = "data/world_state.db"):
        self._db_path = db_path

    async def init(self) -> None:
        """建表 / Create tables."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tick_states (
                    tick INTEGER PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    # ── 写入 ──
    async def save(self, state: dict[str, Any], tick: int) -> None:
        """保存当前 tick 的完整 State / Save full state for a tick."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO tick_states (tick, state_json) VALUES (?, ?)",
                (tick, json.dumps(state, default=str)),
            )
            await db.commit()

    # ── 读取 ──
    async def load(self, tick: int) -> dict[str, Any] | None:
        """读取指定 tick 的 State / Load state for a specific tick."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT state_json FROM tick_states WHERE tick = ?", (tick,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None

    async def load_latest(self) -> dict[str, Any] | None:
        """读取最新 tick 的 State / Load latest state."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT tick, state_json FROM tick_states ORDER BY tick DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {**json.loads(row[1]), "tick": row[0]}
                return None

    # ── 回退 ──
    async def rollback(self, tick: int) -> None:
        """删除 tick 之后的所有状态 / Delete states after tick."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM tick_states WHERE tick > ?", (tick,))
            await db.commit()

    # ── 查询 ──
    async def get_tick_count(self) -> int:
        """取得已保存的 tick 数量."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT MAX(tick) FROM tick_states") as cursor:
                row = await cursor.fetchone()
                return (row[0] or -1) + 1

    async def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取最近 N 个 tick 的历史 / Get recent tick history."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT tick, state_json FROM tick_states ORDER BY tick DESC LIMIT ?",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [{**json.loads(r[1]), "tick": r[0]} for r in rows]

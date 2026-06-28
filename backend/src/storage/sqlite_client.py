"""SQLite 客户端——封装所有裸 SQL，不涉及业务."""

import json
from typing import Any

import aiosqlite


class SQLiteClient:
    """封装 SQLite 建表/增删查，对外只暴露方法名，不暴露 SQL."""

    def __init__(self, db_path: str = "data/world_state.db"):
        self._db_path = db_path

    async def _connect(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self._db_path)

    # ── 建表 ──
    async def create_character_table(self) -> None:
        async with await self._connect() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id TEXT PRIMARY KEY,
                    character_type TEXT NOT NULL,
                    data_json TEXT NOT NULL
                )
            """)
            await db.commit()

    # ── 写 ──
    async def insert_character(self, character_id: str, character_type: str, data: dict[str, Any]) -> None:
        async with await self._connect() as db:
            await db.execute(
                "INSERT OR REPLACE INTO characters (id, character_type, data_json) VALUES (?, ?, ?)",
                (character_id, character_type, json.dumps(data, default=str)),
            )
            await db.commit()

    # ── 查 ──
    async def find_character(self, character_id: str, character_type: str) -> dict[str, Any] | None:
        async with await self._connect() as db:
            async with db.execute(
                "SELECT data_json FROM characters WHERE id = ? AND character_type = ?",
                (character_id, character_type),
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else None

    async def find_all_characters(self, character_type: str) -> list[dict[str, Any]]:
        async with await self._connect() as db:
            async with db.execute(
                "SELECT data_json FROM characters WHERE character_type = ?", (character_type,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [json.loads(r[0]) for r in rows]

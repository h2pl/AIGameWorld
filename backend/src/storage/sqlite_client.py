"""SQLite 客户端——只负责裸 DB 操作，不涉及业务。

职责：连接管理 / 建表 / 执行 SQL / 事务。
"""

import aiosqlite


class SQLiteClient:
    """SQLite 裸操作客户端."""

    def __init__(self, db_path: str = "data/world_state.db"):
        self._db_path = db_path

    async def connect(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self._db_path)

    async def execute(self, sql: str, *params) -> None:
        async with await self.connect() as db:
            await db.execute(sql, params)
            await db.commit()

    async def fetch_one(self, sql: str, *params) -> tuple | None:
        async with await self.connect() as db:
            async with db.execute(sql, params) as cursor:
                return await cursor.fetchone()

    async def fetch_all(self, sql: str, *params) -> list[tuple]:
        async with await self.connect() as db:
            async with db.execute(sql, params) as cursor:
                return await cursor.fetchall()

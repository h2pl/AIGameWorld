"""SQLite 裸操作——封装 connect / execute / fetch / schema，零业务."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiosqlite


class SQLiteClient:
    """SQLite 连接管理 + 裸 SQL 执行."""

    def __init__(self, db_path: str | Path = "data/world_db.db"):
        self._db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        self._db.row_factory = aiosqlite.Row

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def init_schema(self) -> None:
        """执行 schema.sql / Run schema.sql."""
        schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        await self._db.executescript(schema)
        await self._db.commit()

    @property
    def db(self) -> aiosqlite.Connection:
        if not self._db:
            raise RuntimeError("SQLiteClient not connected. Call connect() first.")
        return self._db

    async def execute(self, sql: str, params: tuple = ()) -> None:
        await self._db.execute(sql, params)

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        async with self._db.execute(sql, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        async with self._db.execute(sql, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def commit(self) -> None:
        await self._db.commit()

    async def begin(self) -> None:
        await self._db.execute("BEGIN")

    @asynccontextmanager
    async def transaction(self):
        """事务上下文管理器——自动 commit/rollback."""
        await self.begin()
        try:
            yield
            await self.commit()
        except Exception:
            await self._db.rollback()
            raise

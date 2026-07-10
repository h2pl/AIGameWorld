"""SQLite 裸操作——封装 connect / execute / fetch / schema，零业务."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiosqlite

from ..utils.logging import get_logger
from ..utils.tracing import trace_db

logger = get_logger(__name__)


class SQLiteClient:
    """SQLite 连接管理 + 裸 SQL 执行."""

    def __init__(self, db_path: str | Path = "data/world_db.db"):
        self._db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        self._db.row_factory = aiosqlite.Row
        # WAL 模式减少并发读写锁 / WAL mode reduces concurrent lock contention
        await self._db.execute("PRAGMA journal_mode=WAL")
        logger.info("[storage] connected %s", self._db_path.name)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("[storage] closed")

    async def init_schema(self) -> None:
        """执行 schema.sql 并应用兼容性迁移 / Execute schema.sql and apply compatibility migrations."""
        schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        await self._db.executescript(schema)
        await self._db.commit()
        await self._migrate_drop_map_key()
        logger.info("[storage] schema initialized")

    async def _migrate_drop_map_key(self) -> None:
        """删除 scenes 表历史 map_key 列 / Drop legacy map_key column from scenes."""
        rows = await self.fetch_all("PRAGMA table_info(scenes)")
        if not any(r.get("name") == "map_key" for r in rows):
            return
        logger.info("[storage] migrating: dropping scenes.map_key")
        await self.execute("PRAGMA foreign_keys=OFF")
        await self.execute("BEGIN")
        try:
            await self.execute(
                "CREATE TABLE scenes_new ("
                "id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, "
                "description TEXT, spawn_x INTEGER NOT NULL DEFAULT 0, "
                "spawn_y INTEGER NOT NULL DEFAULT 0, map_width INTEGER NOT NULL DEFAULT 40, "
                "map_height INTEGER NOT NULL DEFAULT 40, world_id TEXT NOT NULL, "
                "tilemap_summary TEXT, ext_json TEXT NOT NULL DEFAULT '{}', "
                "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), "
                "updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))"
                ")"
            )
            await self.execute(
                "INSERT INTO scenes_new (id, name, type, description, spawn_x, spawn_y, "
                "map_width, map_height, world_id, tilemap_summary, ext_json, created_at, updated_at) "
                "SELECT id, name, type, description, spawn_x, spawn_y, map_width, map_height, "
                "world_id, tilemap_summary, ext_json, created_at, updated_at FROM scenes"
            )
            await self.execute("DROP TABLE scenes")
            await self.execute("ALTER TABLE scenes_new RENAME TO scenes")
            await self.execute("CREATE INDEX IF NOT EXISTS idx_scenes_world ON scenes(world_id)")
            await self.execute("COMMIT")
        except Exception:
            await self.execute("ROLLBACK")
            raise
        finally:
            await self.execute("PRAGMA foreign_keys=ON")

    @property
    def db(self) -> aiosqlite.Connection:
        if not self._db:
            raise RuntimeError("SQLiteClient not connected. Call connect() first.")
        return self._db

    async def execute(self, sql: str, params: tuple = ()) -> None:
        async with trace_db("execute", sql):
            await self._db.execute(sql, params)

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        async with trace_db("fetch_all", sql):
            async with self._db.execute(sql, params) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        async with trace_db("fetch_one", sql):
            async with self._db.execute(sql, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def commit(self) -> None:
        async with trace_db("commit"):
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

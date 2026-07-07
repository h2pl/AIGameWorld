"""SQLiteClient 兼容性迁移测试 / Migration tests for SQLiteClient."""

import pytest

from src.storage.sqlite_client import SQLiteClient


class TestMapKeyMigration:
    @pytest.mark.asyncio
    async def test_init_schema_drops_legacy_map_key_column(self):
        """历史数据库中存在 scenes.map_key 列时，init_schema 应自动删除."""
        client = SQLiteClient(":memory:")
        await client.connect()

        # 模拟旧表结构 / Simulate old schema with map_key
        await client.execute(
            "CREATE TABLE scenes ("
            "id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, description TEXT, "
            "map_key TEXT DEFAULT '', spawn_x INTEGER NOT NULL DEFAULT 0, "
            "spawn_y INTEGER NOT NULL DEFAULT 0, map_width INTEGER NOT NULL DEFAULT 40, "
            "map_height INTEGER NOT NULL DEFAULT 40, world_id TEXT NOT NULL, "
            "tilemap_summary TEXT, ext_json TEXT NOT NULL DEFAULT '{}', "
            "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), "
            "updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))"
            ")"
        )
        await client.execute(
            "INSERT INTO scenes (id, name, type, map_key, world_id) VALUES (?, ?, ?, ?, ?)",
            ("scene-1", "Tavern", "indoor", "tavern-map", "world-1"),
        )
        await client.commit()

        # 执行迁移 / Run migrations
        await client.init_schema()

        cols = await client.fetch_all("PRAGMA table_info(scenes)")
        names = {c["name"] for c in cols}
        assert "map_key" not in names
        assert "id" in names
        assert "name" in names

        # 数据保留 / Data preserved
        row = await client.fetch_one("SELECT id, name FROM scenes WHERE id = ?", ("scene-1",))
        assert row["name"] == "Tavern"

    @pytest.mark.asyncio
    async def test_init_schema_ignores_when_no_map_key(self):
        """新数据库没有 map_key 列时，迁移应直接跳过."""
        client = SQLiteClient(":memory:")
        await client.connect()
        await client.init_schema()

        cols = await client.fetch_all("PRAGMA table_info(scenes)")
        names = {c["name"] for c in cols}
        assert "map_key" not in names

"""storage + repository 集成测试——真实 SQLite / Integration tests with real SQLite."""

import os
import tempfile
from pathlib import Path

import pytest

from src.storage.sqlite_client import SQLiteClient

# ── Fixtures / 测试夹具 ──


@pytest.fixture
async def db():
    """临时 SQLite 数据库."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    client = SQLiteClient(path)
    await client.connect()
    await client.init_schema()
    yield client
    await client.close()
    Path(path).unlink()


class TestSQLiteClient:
    # ── Schema / 数据库结构 ──
    async def test_init_schema_creates_tables(self, db):
        tables = await db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        names = [t["name"] for t in tables]
        assert "player_characters" in names
        assert "actors" in names
        assert "dm_records" in names
        assert "tick_events" in names

    async def test_world_meta_write_read(self, db):
        # world_meta 表已删除，改用 worlds 表测试 INSERT
        await db.execute(
            "INSERT OR REPLACE INTO worlds (id, name) VALUES (?, ?)",
            ("test_world", "Test World"),
        )
        await db.commit()
        row = await db.fetch_one("SELECT name FROM worlds WHERE id = ?", ("test_world",))
        assert row["name"] == "Test World"

    async def test_narrative_insert(self, db):
        # 用 tick_events 表测试 insert / Use tick_events table for insert test
        await db.execute(
            "INSERT INTO tick_events (tick, type, payload, world_id) VALUES (?, ?, ?, ?)",
            (1, "dm_create", "{}", "test"),
        )
        await db.commit()
        rows = await db.fetch_all("SELECT * FROM tick_events WHERE world_id = ?", ("test",))
        assert len(rows) == 1

    async def test_transaction_context(self, db):
        async with db.transaction():
            await db.execute(
                "INSERT INTO tick_events (tick, type, payload, world_id) VALUES (?, ?, ?, ?)",
                (2, "pc_talk", "{}", "test_txn"),
            )
        rows = await db.fetch_all("SELECT * FROM tick_events WHERE world_id = ?", ("test_txn",))
        assert len(rows) == 1

    async def test_transaction_rollback(self, db):
        try:
            async with db.transaction():
                await db.execute(
                    "INSERT INTO tick_events (tick, type, payload, world_id) VALUES (?, ?, ?, ?)",
                    (3, "scene_setup", "{}", "test_rollback"),
                )
                raise RuntimeError("forced error")
        except RuntimeError:
            pass
        rows = await db.fetch_all(
            "SELECT * FROM tick_events WHERE world_id = ?", ("test_rollback",)
        )
        assert len(rows) == 0


# ── Character Repo 集成测试 / Character Repository integration tests ──
class TestPcRepo:
    async def test_save_and_load_pc(self, db):
        from src.domain import (
            PlayerCharacter,
        )
        from src.repository.pc_repo import PcRepo

        repo = PcRepo(db)
        pc = PlayerCharacter(
            id="test_pc",
            name="TestHero",
            role="fighter",
        )
        await repo.save_pc(pc)
        await db.commit()

        pcs = await repo.load_pcs()
        assert len(pcs) == 1
        assert pcs[0].id == "test_pc"
        assert pcs[0].name == "TestHero"

    async def test_save_and_load_actor(self, db):
        from src.domain import Actor
        from src.repository.pc_repo import PcRepo

        repo = PcRepo(db)
        actor = Actor(
            id="test_actor",
            name="Greta",
            role="innkeeper",
        )
        await repo.save_actor(actor)
        await db.commit()

        actors = await repo.load_actors()
        assert len(actors) == 1
        assert actors[0].id == "test_actor"

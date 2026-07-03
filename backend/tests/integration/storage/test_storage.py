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
        assert "narratives" in names
        assert "tick_events" in names

    async def test_world_meta_write_read(self, db):
        await db.execute(
            "INSERT OR REPLACE INTO world_meta (key, value) VALUES (?, ?)",
            ("test_key", "test_value"),
        )
        await db.commit()
        row = await db.fetch_one("SELECT value FROM world_meta WHERE key = ?", ("test_key",))
        assert row["value"] == "test_value"

    async def test_narrative_insert(self, db):
        await db.execute("INSERT INTO narratives (tick, content) VALUES (?, ?)", (0, "Hello"))
        await db.commit()
        rows = await db.fetch_all("SELECT * FROM narratives")
        assert len(rows) == 1
        assert rows[0]["content"] == "Hello"

    async def test_transaction_context(self, db):
        async with db.transaction():
            await db.execute(
                "INSERT INTO narratives (tick, content) VALUES (?, ?)", (1, "In transaction")
            )
        rows = await db.fetch_all("SELECT * FROM narratives WHERE tick = 1")
        assert len(rows) == 1

    # ── 事务回滚 / Transaction rollback ──
    async def test_transaction_rollback(self, db):
        try:
            async with db.transaction():
                await db.execute(
                    "INSERT INTO narratives (tick, content) VALUES (?, ?)", (2, "Should rollback")
                )
                raise RuntimeError("forced error")
        except RuntimeError:
            pass
        rows = await db.fetch_all("SELECT * FROM narratives WHERE tick = 2")
        assert len(rows) == 0


# ── Character Repo 集成测试 / Character Repository integration tests ──
class TestPcRepo:
    async def test_save_and_load_pc(self, db):
        from src.domain import (
            PlayerCharacter,
        )

        from .pc_repo import PcRepo

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

        from .pc_repo import PcRepo

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

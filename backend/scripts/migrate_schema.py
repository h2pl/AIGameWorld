"""DB Schema 迁移脚本 / Schema migration script——删旧表建新表."""

# 用法: python scripts/migrate_schema.py
import asyncio

from src.storage.sqlite_client import SQLiteClient


async def m():
    db = SQLiteClient("data/world_db.db")
    await db.connect()
    await db.execute("DROP TABLE IF EXISTS dm_records")
    await db.execute(
        "CREATE TABLE IF NOT EXISTS dm_records (id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL, tick INTEGER NOT NULL, plot_brief TEXT NOT NULL DEFAULT '', hints_json TEXT NOT NULL DEFAULT '[]', dm_narrative TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), UNIQUE(world_id, tick))"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_dm_records_world_tick ON dm_records(world_id, tick)"
    )
    await db.execute(
        "CREATE TABLE IF NOT EXISTS story_summaries (id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL, tick_start INTEGER NOT NULL, tick_end INTEGER NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), UNIQUE(world_id, tick_start))"
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_summaries_world ON story_summaries(world_id)")
    rows = await db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    print([r["name"] for r in rows])
    await db.close()


asyncio.run(m())

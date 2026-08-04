"""Create missing tables in DB files."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
DBS = [p for p in [
    ROOT / "data/world_db.db",
    ROOT / "backend/data/world_db.db",
    ROOT / "data/live_test.db",
    ROOT / "backend/data/live_test.db",
    ROOT / "data/warcraft.db",
] if p.exists()]

DDL = """
CREATE TABLE IF NOT EXISTS tick_messages (
    id TEXT NOT NULL, tick INTEGER NOT NULL, world_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'building', is_last INTEGER NOT NULL DEFAULT 0,
    ext_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')), acked_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tick_message_id_tick ON tick_messages(id, tick);

CREATE TABLE IF NOT EXISTS tick_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, tick_message_id TEXT NOT NULL,
    tick INTEGER NOT NULL, type TEXT NOT NULL, payload TEXT NOT NULL,
    ext_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dm_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL,
    tick INTEGER NOT NULL, plot_brief TEXT NOT NULL DEFAULT '',
    hint_list TEXT NOT NULL DEFAULT '[]', dm_narrative TEXT NOT NULL DEFAULT '',
    ext_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, tick)
);

CREATE TABLE IF NOT EXISTS story_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL,
    tick_start INTEGER NOT NULL, tick_end INTEGER NOT NULL,
    summary TEXT NOT NULL, ext_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, tick_start)
);
"""

for db_path in DBS:
    conn = sqlite3.connect(str(db_path))
    conn.executescript(DDL)
    conn.commit()
    conn.close()
    print(f"[OK] {db_path.name}")
print("Done.")

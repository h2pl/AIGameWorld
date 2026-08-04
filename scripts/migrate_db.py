"""Complete DB schema migration — drop/rename/add columns."""
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


def _table_exists(c, table: str) -> bool:
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
              (table,))
    return c.fetchone() is not None


def _has(c, table: str, col: str) -> bool:
    if not _table_exists(c, table):
        return False
    c.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in c.fetchall())


def safe_op(c, table: str, fn, *args):
    """Skip operation if table doesn't exist."""
    if not _table_exists(c, table):
        return
    fn(*args)


def drop(c, table: str, col: str):
    if _has(c, table, col):
        c.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
        print(f"  DROP {table}.{col}")


def rename(c, table: str, old: str, new: str):
    if _has(c, table, old) and not _has(c, table, new):
        c.execute(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}")
        print(f"  RENAME {table}.{old} -> {new}")


def add(c, table: str, col_def: str):
    col_name = col_def.split()[0]
    if not _has(c, table, col_name):
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        print(f"  ADD {table}.{col_def}")


def migrate(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    print(f"[{db_path.name}]")

    # ── player_characters ──
    safe_op(c, "player_characters", drop, c, "player_characters", "reflection_threshold")
    safe_op(c, "player_characters", rename, c, "player_characters", "character_arc_json", "arc_json")

    # ── actors ──
    safe_op(c, "actors", drop, c, "actors", "reflection_threshold")
    safe_op(c, "actors", drop, c, "actors", "service_arcs_json")

    # ── scenes ──
    for col in ("exits_json", "landmarks_json", "environment_json", "world_name"):
        safe_op(c, "scenes", drop, c, "scenes", col)

    # ── items ──
    safe_op(c, "items", drop, c, "items", "world_name")
    safe_op(c, "items", rename, c, "items", "data_json", "data")

    # ── scene_objects ──
    safe_op(c, "scene_objects", rename, c, "scene_objects", "interact_data_json", "interact_data")

    # ── tick_events ──
    safe_op(c, "tick_events", rename, c, "tick_events", "msg_tick", "tick")

    # ── add ext_json to all domain tables ──
    for t in [
        "worlds", "player_characters", "actors", "scenes", "items",
        "scene_objects", "tick_messages", "tick_events", "dm_records",
        "story_summaries",
    ]:
        safe_op(c, t, add, c, t, "ext_json TEXT NOT NULL DEFAULT '{}'")

    # ── tick_messages ──
    safe_op(c, "tick_messages", add, c, "tick_messages", "is_last INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()
    print(f"[OK] {db_path.name}\n")


if __name__ == "__main__":
    for db in DBS:
        migrate(db)
    print("Done.")

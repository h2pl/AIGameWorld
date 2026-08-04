"""以 schema.sql 为准重建 DB，删旧表，修正列名."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent / "backend"
DB = ROOT / "data" / "world_db.db"
SCHEMA = ROOT / "src" / "storage" / "schema.sql"

conn = sqlite3.connect(str(DB))
c = conn.cursor()

# 1. 删旧表
for t in ["narratives", "world_meta", "quests"]:
    c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
    if c.fetchone():
        c.execute(f"DROP TABLE {t}")
        print(f"DROP {t}")

# 2. dm_records: hints_json → hint_list（如果存在）
try:
    c.execute("ALTER TABLE dm_records RENAME COLUMN hints_json TO hint_list")
    print("RENAME hints_json → hint_list")
except Exception:
    print("hint_list already ok")

# 3. scenes: 删 pack_name（如果存在）
try:
    c.execute("SELECT pack_name FROM scenes LIMIT 0")
    c.execute("ALTER TABLE scenes DROP COLUMN pack_name")
    print("DROP scenes.pack_name")
except Exception:
    print("scenes.pack_name already gone")

# 4. scene_objects: 补 updated_at（如果不存在，SQLite 不允许非空默认表达式，先加 NULL 再 UPDATE）
try:
    c.execute("SELECT updated_at FROM scene_objects LIMIT 0")
except Exception:
    c.execute("ALTER TABLE scene_objects ADD COLUMN updated_at TEXT")
    c.execute("UPDATE scene_objects SET updated_at = datetime('now') WHERE updated_at IS NULL")
    print("ADD scene_objects.updated_at")

conn.commit()

# 验证
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in c.fetchall() if not r[0].startswith("sqlite_")]
print(f"\nFinal tables ({len(tables)}):")
for t in tables:
    c.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in c.fetchall()]
    print(f"  {t}: {cols}")

conn.close()
print("\nDone.")

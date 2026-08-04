"""删除旧版 events / messages 表 / Drop legacy events and messages tables."""
import sqlite3
from pathlib import Path

# 所有 DB 文件 / All DB files
ROOT = Path(__file__).parent.parent
DBS = [p for p in [
    ROOT / "data/world_db.db",
    ROOT / "backend/data/world_db.db",
    ROOT / "data/live_test.db",
    ROOT / "backend/data/live_test.db",
    ROOT / "data/warcraft.db",
] if p.exists()]

# 遍历删除 / Iterate and drop
for db_path in DBS:
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    for t in ["events", "messages"]:
        c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
        if c.fetchone():
            c.execute(f"DROP TABLE {t}")
            print(f"[{db_path.name}] DROP {t}")
    conn.commit()
    conn.close()
print("Done.")

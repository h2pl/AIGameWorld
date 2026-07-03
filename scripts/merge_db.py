"""Merge data/world_db.db into backend/data/world_db.db (INSERT OR IGNORE to skip duplicates)."""
import sqlite3

src = sqlite3.connect("data/world_db.db")
dst = sqlite3.connect("backend/data/world_db.db")
sc = src.cursor()
dc = dst.cursor()

TABLES = [
    "worlds", "scenes", "player_characters", "actors",
    "items", "scene_objects", "quests",
]

for table in TABLES:
    try:
        sc.execute(f"SELECT * FROM {table}")
        rows = sc.fetchall()
        cols = [d[1] for d in sc.description]
        if not rows:
            continue
        for r in rows:
            placeholders = ",".join(["?"] * len(r))
            dc.execute(
                f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                r,
            )
        print(f"  {table}: {len(rows)} rows")
    except Exception as e:
        print(f"  {table}: skip ({e})")

dst.commit()

# verify
dc.execute("SELECT COUNT(*) FROM worlds")
print(f"worlds: {dc.fetchone()[0]}")
dc.execute("SELECT COUNT(*) FROM player_characters")
print(f"PCs: {dc.fetchone()[0]}")
dc.execute("SELECT COUNT(*) FROM actors")
print(f"actors: {dc.fetchone()[0]}")
dc.execute("SELECT COUNT(*) FROM scenes")
print(f"scenes: {dc.fetchone()[0]}")
print("Done.")

src.close()
dst.close()

"""Merge data/world_db.db into backend/data/world_db.db (INSERT OR IGNORE to skip duplicates).

合并种子数据库到后端数据库，重复记录自动跳过 / Merge seed DB into backend DB, skip duplicates.
"""
import sqlite3

# 源数据库（种子数据）/ Source seed database
src = sqlite3.connect("data/world_db.db")
# 目标数据库（后端运行库）/ Destination backend database
dst = sqlite3.connect("backend/data/world_db.db")
sc = src.cursor()  # 源游标 / Source cursor
dc = dst.cursor()  # 目标游标 / Destination cursor

# 需要合并的表 / Tables to merge
TABLES = [
    "worlds", "scenes", "player_characters", "actors",
    "items", "scene_objects", "quests",
]

# 逐表复制数据 / Copy table by table
for table in TABLES:
    try:
        sc.execute(f"SELECT * FROM {table}")  # 读取源表 / Read source table
        rows = sc.fetchall()
        cols: list[str] = [str(d[1]) for d in sc.description]  # 列名 / Column names
        if not rows:
            continue  # 空表跳过 / Skip empty table
        for r in rows:
            row = list(r)
            placeholders = ",".join(["?"] * len(row))  # SQL 占位符 / SQL placeholders
            col_list = ",".join(cols)
            dc.execute(
                f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})",
                row,
            )
        print(f"  {table}: {len(rows)} rows")
    except Exception as e:
        print(f"  {table}: skip ({e})")  # 出错继续下一张表 / Continue on error

# 提交写入 / Commit writes
dst.commit()

# 校验行数 / Verify row counts
dc.execute("SELECT COUNT(*) FROM worlds")
print(f"worlds: {dc.fetchone()[0]}")
dc.execute("SELECT COUNT(*) FROM player_characters")
print(f"PCs: {dc.fetchone()[0]}")
dc.execute("SELECT COUNT(*) FROM actors")
print(f"actors: {dc.fetchone()[0]}")
dc.execute("SELECT COUNT(*) FROM scenes")
print(f"scenes: {dc.fetchone()[0]}")
print("Done.")

# 关闭连接 / Close connections
src.close()
dst.close()

"""DB Schema 迁移脚本 / Schema migration script.

直接复用 SQLiteClient.init_schema()（执行 schema.sql + 兼容性迁移），
保证本地 data/world_db.db 与权威 schema.sql 完全一致。

# 用法: python scripts/migrate_schema.py
"""

import asyncio

from src.storage.sqlite_client import SQLiteClient


async def m():
    db = SQLiteClient("data/world_db.db")
    await db.connect()
    # init_schema 执行 schema.sql + 全部 _migrate_* 兼容迁移，对齐权威表结构
    await db.init_schema()
    rows = await db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    print("tables:", [r["name"] for r in rows])
    cols = await db.fetch_all("PRAGMA table_info(worlds)")
    print("worlds columns:", [c["name"] for c in cols])
    await db.close()


asyncio.run(m())

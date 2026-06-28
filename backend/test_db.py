"""快速验证 DB 内容."""
import asyncio, sys
sys.path.insert(0, ".")

async def check():
    from src.storage.sqlite_client import SQLiteClient
    db = SQLiteClient("data/world_state.db")
    await db.connect()

    tables = await db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    print(f"Tables: {len(tables)} -> {[t['name'] for t in tables[:5]]}...")

    pcs = await db.fetch_all("SELECT id, name, role FROM player_characters")
    print(f"PCs: {len(pcs)} -> {[(r['name'], r['role']) for r in pcs]}")

    actors = await db.fetch_all("SELECT id, name FROM actors")
    print(f"Actors: {len(actors)} -> {[r['name'] for r in actors]}")

    narr = await db.fetch_all("SELECT tick, substr(content,1,60) as c FROM narratives")
    print(f"Narratives: {len(narr)} -> {[(r['tick'], r['c']) for r in narr]}")

    tick = await db.fetch_one("SELECT value FROM world_meta WHERE key='current_tick'")
    print(f"Current tick: {tick['value'] if tick else 'NOT SET'}")

    await db.close()

asyncio.run(check())

"""直接通过 repo 层把 starraft 充实版写入 mock.db（绕过 HTTP，避免锁竞争）。

等价于 POST /api/world/create 的内部逻辑：world + scenes + pcs + actors + items + scene_objects。
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.storage.sqlite_client import SQLiteClient
from src.domain import World, Scene, PlayerCharacter, Actor, Item, SceneObject
from src.repository.world_repo import WorldRepo
from src.repository.scene_repo import SceneRepo
from src.repository.pc_repo import PcRepo
from src.repository.actor_repo import ActorRepo
from src.repository.item_repo import ItemRepo


async def main():
    data = json.loads(Path(__file__).resolve().parent.joinpath("world_def.json").read_text(encoding="utf-8"))
    db = SQLiteClient(str(Path(__file__).resolve().parents[2] / "backend" / "data" / "mock.db"))
    await db.connect()
    await db.init_schema()

    world_repo = WorldRepo(db)
    scene_repo = SceneRepo(db)
    pc_repo = PcRepo(db)
    actor_repo = ActorRepo(db)
    item_repo = ItemRepo(db)

    wid = data["world"]["id"]
    # 直接按 id 幂等覆盖（不先 DELETE，避免外键约束冲突导致整事务回滚）。
    # world_repo.create 已用 ON CONFLICT(id) DO UPDATE；其余 repo 的 save 为 INSERT OR REPLACE。

    # world
    await world_repo.create(World(**data["world"]))
    # scenes
    for sc in data["scenes"]:
        await scene_repo.save_scene(Scene(**sc), wid)
        # tilemap_summary 单独写（save_scene 可能不含）
        if sc.get("tilemap_summary"):
            await scene_repo.save_tilemap_summary(sc["id"], sc["tilemap_summary"])
    # pcs
    for pc in data["pcs"]:
        await pc_repo.save(PlayerCharacter(**pc))
    # actors
    for ac in data["actors"]:
        await actor_repo.save(Actor(**ac))
    # items
    for it in data["items"]:
        await item_repo.save(Item(**it))
    # scene_objects
    for so in data["scene_objects"]:
        await scene_repo.save_object(SceneObject(**so))

    # 关闭前直接查询 DB 实际计数，确认写入
    for t in ["scenes", "player_characters", "actors", "items", "scene_objects"]:
        n = await db.fetch_one(f"SELECT COUNT(*) AS c FROM {t} WHERE world_id=?", (wid,))
        print(f"  DB {t} = {n['c']}")

    print(f"OK starraft: scenes={len(data['scenes'])} pcs={len(data['pcs'])} "
          f"actors={len(data['actors'])} items={len(data['items'])} objects={len(data['scene_objects'])}")
    # 关键：WAL 模式下显式 checkpoint，把写入合并进主库文件，否则 server 长连接读不到。
    await db._db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())

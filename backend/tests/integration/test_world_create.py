"""集成测试——POST /api/world/create 全量写入 / Integration test for world creation.

验证完整世界定义（world + scenes + pcs + actors + items + scene_objects）
一次性写入所有表，且 world_id 正确关联到每个实体。
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from src.server import app
from src.storage.sqlite_client import SQLiteClient


@pytest.fixture
def client(tmp_path):
    """临时 SQLite 注入 app.state.db，避免污染真实 DB / Temp DB injected into app.state."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    db = SQLiteClient(str(tmp_path / "create_test.db"))
    loop.run_until_complete(db.connect())
    loop.run_until_complete(db.init_schema())
    app.state.db = db
    yield TestClient(app)
    loop.run_until_complete(db.close())
    app.state.db = None
    loop.close()


def _payload(world_id: str) -> dict:
    """构造一个最小但完整的世界定义 / Build a minimal full world definition."""
    return {
        "world": {
            "id": world_id,
            "name": "测试世界",
            "description": "集成测试世界",
            "version": "1.0.0",
            "rule_set": "dnd_5e_srd",
            "author": "test",
            "starting_scene_id": f"{world_id}_town",
            "status": "init",
        },
        "scenes": [
            {
                "id": f"{world_id}_town",
                "name": "主城",
                "type": "town",
                "description": "冒险起点",
                "spawn_x": 9,
                "spawn_y": 10,
                "map_width": 50,
                "map_height": 50,
                "world_id": world_id,
            }
        ],
        "pcs": [
            {
                "id": f"{world_id}_hero",
                "name": "勇士",
                "role": "fighter",
                "scene_id": f"{world_id}_town",
                "position_x": 8,
                "position_y": 10,
                "world_id": world_id,
            }
        ],
        "actors": [
            {
                "id": f"{world_id}_guard",
                "name": "守卫",
                "role": "guard",
                "scene_id": f"{world_id}_town",
                "position_x": 22,
                "position_y": 18,
                "world_id": world_id,
            }
        ],
        "items": [
            {
                "id": f"{world_id}_relic",
                "name": "圣物",
                "item_type": "key",
                "rarity": "uncommon",
                "description": "关键物品",
                "world_id": world_id,
            }
        ],
        "scene_objects": [
            {
                "id": f"{world_id}_shrine",
                "name": "祭坛",
                "object_type": "mechanism",
                "scene_id": f"{world_id}_town",
                "position_x": 14,
                "position_y": 12,
                "world_id": world_id,
            }
        ],
    }


def test_create_world_success(client):
    """完整世界应一次性写入所有表，并返回正确计数 / Full world writes all tables."""
    wid = "test_create_1"
    resp = client.post("/api/world/create", json=_payload(wid))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    assert data["world_id"] == wid
    assert data["counts"] == {
        "scenes": 1,
        "pcs": 1,
        "actors": 1,
        "items": 1,
        "scene_objects": 1,
    }


def test_create_world_persists_world_id(client):
    """所有实体的 world_id 必须正确写入（核心关联完整性）/ world_id must be persisted on every entity."""
    import asyncio

    wid = "test_create_2"
    resp = client.post("/api/world/create", json=_payload(wid))
    assert resp.status_code == 200, resp.text

    db = app.state.db

    async def _check():
        from src.repository.actor_repo import ActorRepo
        from src.repository.item_repo import ItemRepo
        from src.repository.pc_repo import PcRepo
        from src.repository.scene_repo import SceneRepo
        from src.repository.world_repo import WorldRepo

        assert await WorldRepo(db).get(wid) is not None
        scenes = await SceneRepo(db).list_scenes(wid)
        assert len(scenes) == 1 and scenes[0].world_id == wid
        pcs = await PcRepo(db).load_all(wid)
        assert len(pcs) == 1 and pcs[0].world_id == wid
        actors = await ActorRepo(db).load_all(wid)
        assert len(actors) == 1 and actors[0].world_id == wid
        items = await ItemRepo(db).list_by_world(wid)
        assert len(items) == 1
        objs = await SceneRepo(db).list_objects_by_world(wid)
        assert len(objs) == 1

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_check())
    finally:
        loop.close()


def test_create_world_idempotent(client):
    """重复创建同一 world_id 不报错（INSERT OR REPLACE）/ Re-create same id is idempotent."""
    wid = "test_create_3"
    p = _payload(wid)
    r1 = client.post("/api/world/create", json=p)
    r2 = client.post("/api/world/create", json=p)
    assert r1.status_code == 200 and r2.status_code == 200
    # 计数仍应为 1（覆盖而非重复插入）
    assert r2.json()["counts"]["scenes"] == 1

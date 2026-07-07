"""E2E——真实 LLM 全链路：启动→产 tick→验证 DB→拉取→ACK.

运行：pytest tests/e2e/test_live_tick.py -v -s -m "slow"
前提：LLM provider 可用（config.yaml llm_provider 配置正确）
"""

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.world import World
from src.repository.world_repo import WorldRepo
from src.server import app
from src.storage.sqlite_client import SQLiteClient


@pytest.fixture
async def client():
    """真实 SQLite + 真实 App / Real SQLite + real app."""
    db = SQLiteClient("data/world_db.db")
    app.state.db = db
    await db.connect()
    await db.init_schema()
    await WorldRepo(db).create(World(id="e2e_live", name="E2E 真实测试"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    if getattr(app.state, "db", None):
        await app.state.db.close()
        app.state.db = None


@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_pipeline_real_llm(client):
    """完整流程：启动→等tick→读DB→拉取→ACK→验证消费.

    日志关键字：[api] [msg] [phase] [llm]
    """
    WORLD = "e2e_live"
    started = time.monotonic()

    # 1. 世界初始状态 / World initial state
    r = await client.get(f"/api/world/{WORLD}/state")
    assert r.status_code == 200, r.text
    assert r.json()["world_id"] == WORLD
    print(f"\n✅ 1. world state ok ({(time.monotonic() - started):.1f}s)")

    # 2. 运行一个 tick / Run one tick
    r = await client.post(f"/api/world/{WORLD}/tick/batch/1")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        r = await client.get(f"/api/world/{WORLD}/loop/status")
        status = r.json()
        if not status["batch_running"] and status["batch_completed"] == 1:
            break
        await asyncio.sleep(0.5)
    else:
        pytest.fail("tick 未在 120s 内产出")

    elapsed = time.monotonic() - started
    print(f"✅ 2. tick produced ({elapsed:.1f}s)")

    # 3. 拉取事件 / Pull events
    r = await client.get(f"/api/world/{WORLD}/events?since_tick=0&tick_limit=1")
    assert r.status_code == 200, r.text
    data = r.json()
    events = data.get("events", [])
    assert len(events) > 0, "至少一个事件"
    for ev in events:
        text = ev.get("payload", {}).get("text", ev.get("payload", {}).get("thought", ""))[:60]
        print(f"   [{ev['type']}] {text}")

    # 4. 验证 DB 写入 / Verify DB write
    db = app.state.db
    event_rows = await db.fetch_all(
        "SELECT COUNT(*) as cnt FROM tick_events WHERE world_id=? AND tick=?",
        (WORLD, data["data_tick"]),
    )
    assert event_rows[0]["cnt"] == len(events), f"tick_events 表应有 {len(events)} 条"
    print(f"✅ 3. DB verified: events={event_rows[0]['cnt']}")

    # 5. ACK / Acknowledge display tick
    r = await client.post(f"/api/world/{WORLD}/tick/display/{data['data_tick']}")
    assert r.status_code == 200, r.text
    assert r.json()["display_tick"] == data["data_tick"]
    print(f"✅ 4. ack tick={data['data_tick']}")

    # 6. 事件内容结构 / Validate event structure
    valid_types = {
        "dm_create",
        "scene_setup",
        "scene_objects",
        "character_move",
        "pc_talk",
        "pc_explore",
        "pc_interact",
        "pc_combat",
        "pc_decision",
        "dm_narrative",
    }
    for ev in events:
        assert "type" in ev, "事件必须有 type"
        assert ev["type"] in valid_types, f"未知事件类型 {ev['type']}"
    print(f"✅ 5. event structure valid: {len(events)} events")

    total = time.monotonic() - started
    print(f"\n🎯 全链路通过 ({total:.1f}s)")

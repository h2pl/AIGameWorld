"""E2E——全链路真实 LLM：启动→产 tick→验证 DB→拉取→ACK。

运行：pytest tests/e2e/test_live_tick.py -v -s
前提：LLM provider 可用（config.yaml llm_provider 配置正确）
"""

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    """真实 SQLite + 真实 App / Real SQLite + real app."""
    import src.main as m
    from src.repository.world_repo import WorldRepo
    from src.storage.sqlite_client import SQLiteClient

    db = SQLiteClient("data/world_db.db")
    m._set_db(db)
    m.app.state.sessions = {}
    await db.connect()
    await db.init_schema()
    await WorldRepo(db).create(m.World(id="e2e_live", name="E2E 真实测试"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    sessions = m._get_sessions()
    for mid in list(sessions.keys()):
        s = sessions.pop(mid, None)
        if s and (t := s.get("task")) and not t.done():
            t.cancel()
            await asyncio.sleep(0.1)
    if getattr(m.app.state, "db", None):
        await m._get_db().close()
        m._set_db(None)


class TestLiveTickE2E:
    """真实 LLM 全链路 / Real LLM end-to-end."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_full_pipeline(self, client):
        """完整流程：启动→等tick→读DB→拉取→ACK→验证消费。

        日志关键字：[api] [msg] [phase] [llm]
        """
        WORLD = "e2e_live"
        started = time.monotonic()

        # 1. 启动 session / Start session
        r = await client.post(f"/api/world/{WORLD}/session/start")
        assert r.json()["status"] == "ok"
        print(f"\n✅ 1. session started ({(time.monotonic() - started):.1f}s)")

        # 2. 等 Graph 产出 tick / Wait for producer to generate tick
        tick_data = None
        deadline = time.monotonic() + 60  # 60s 超时
        while time.monotonic() < deadline:
            r = await client.get(f"/api/world/{WORLD}/tick/next")
            msg = r.json()
            if msg["type"] == "tick":
                tick_data = msg["data"]
                break
            elif msg["type"] == "done":
                pytest.fail("unexpected done before first tick")
            await asyncio.sleep(0.5)
        assert tick_data is not None, "tick 未在 60s 内产出"

        tick = tick_data["tick"]
        events = tick_data.get("events", [])
        elapsed = time.monotonic() - started
        print(f"✅ 2. tick={tick} events={len(events)} ({elapsed:.1f}s)")
        for ev in events:
            text = ev.get("text", ev.get("description", ""))[:60]
            print(f"   [{ev['type']}] {text}")

        # 3. 验证 DB 写入 / Verify DB write
        import src.main as m

        db = m._get_db()

        msg_row = await db.fetch_one(
            "SELECT id, tick, status FROM messages WHERE id=? AND status='pending'",
            (WORLD,),
        )
        assert msg_row is not None, "messages 表应有 pending 记录"
        event_rows = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM events WHERE msg_id=? AND msg_tick=?",
            (WORLD, msg_row["tick"]),
        )
        assert event_rows["cnt"] == len(events), f"events 表应有 {len(events)} 条"
        print(f"✅ 3. DB verified: msg={msg_row['status']} events={event_rows['cnt']}")

        # 4. ACK / Acknowledge
        r = await client.post(f"/api/world/{WORLD}/tick/{tick}/ack")
        assert r.json()["status"] == "ok"
        print(f"✅ 4. ack tick={tick}")

        # 5. 验证消费 / Verify consumed
        msg_row_after = await db.fetch_one(
            "SELECT id, status FROM messages WHERE id=? AND tick=?",
            (WORLD, tick),
        )
        assert msg_row_after["status"] == "consumed"
        print(f"✅ 5. consumed verified: status={msg_row_after['status']}")

        # 6. 事件内容结构 / Validate event structure
        assert len(events) > 0, "至少一个事件"
        for ev in events:
            assert "type" in ev, "事件必须有 type"
            assert ev["type"] in (
                "opening",
                "scene_setup",
                "scene_objects",
                "character_move",
                "pc_talk",
                "character_explore",
                "dm_narrative",
            ), f"未知事件类型 {ev['type']}"
        print(f"✅ 6. event structure valid: {len(events)} events")

        total = time.monotonic() - started
        print(f"\n🎯 全链路通过 ({total:.1f}s)")

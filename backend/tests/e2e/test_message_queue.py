"""E2E——消息队列全链路：start → 5 tick → next → ack → done."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    """初始化 :memory: DB + seed test world / Init in-memory DB."""
    import src.main as m
    from src.repository.world_repo import WorldRepo
    from src.storage.sqlite_client import SQLiteClient

    m._db = SQLiteClient(":memory:")
    await m._db.connect()
    await m._db.init_schema()
    await WorldRepo(m._db).create(m.World(id="test", name="test"))
    m._sessions.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    # 清理 / Cleanup
    for mid in list(m._sessions.keys()):
        s = m._sessions.pop(mid, None)
        if s and (t := s.get("task")) and not t.done():
            t.cancel()
            await asyncio.sleep(0.1)
    if m._db:
        await m._db.close()
        m._db = None


class TestMessageQueueE2E:
    @pytest.mark.asyncio
    async def test_health(self, client):
        r = await client.get("/health")
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_world_list(self, client):
        r = await client.get("/api/world")
        worlds = r.json()
        assert any(w["id"] == "test" for w in worlds)

    @pytest.mark.asyncio
    async def test_full_flow_5_ticks(self, client):
        """全链路：start → 拉 5 个 tick → ack → 验证."""
        # 启动 session
        r = await client.post("/api/world/test/session/start")
        assert r.json()["status"] == "ok"

        ticks = []
        for _ in range(5):
            while True:
                r = await client.get("/api/world/test/tick/next")
                msg = r.json()
                if msg["type"] == "tick":
                    data = msg["data"]
                    ticks.append(data)
                    # 验证字段
                    assert "id" in data
                    assert "tick" in data
                    assert "events" in data
                    assert len(data["events"]) > 0
                    # ACK
                    r2 = await client.post(f"/api/world/test/tick/{data['tick']}/ack")
                    assert r2.json()["status"] == "ok"
                    break
                elif msg["type"] == "wait":
                    import asyncio

                    await asyncio.sleep(0.1)
                elif msg["type"] == "done":
                    pytest.fail("unexpected done")

        assert len(ticks) == 5
        # tick 递增
        for i in range(1, len(ticks)):
            assert ticks[i]["tick"] > ticks[i - 1]["tick"]

    @pytest.mark.asyncio
    async def test_pause_resume(self, client):
        """暂停/恢复不丢消息."""
        await client.post("/api/world/test/session/start")
        # 暂停
        r = await client.post("/api/world/test/pause")
        assert r.json()["status"] == "ok"
        # 恢复
        r = await client.post("/api/world/test/resume")
        assert r.json()["status"] == "ok"
        # 验证还能拉 tick
        while True:
            r = await client.get("/api/world/test/tick/next")
            msg = r.json()
            if msg["type"] == "tick":
                assert "tick" in msg["data"]
                break
            elif msg["type"] == "done":
                pytest.fail("unexpected done")

    @pytest.mark.asyncio
    async def test_events_order(self, client):
        """事件按 SEQUENCE 排序."""
        await client.post("/api/world/test/session/start")
        while True:
            r = await client.get("/api/world/test/tick/next")
            msg = r.json()
            if msg["type"] == "tick":
                events = msg["data"]["events"]
                types = [e["type"] for e in events]
                # 验证所有类型在 SEQUENCE 中
                from src.domain.event import SEQUENCE

                order = {t: i for i, t in enumerate(SEQUENCE)}
                for i in range(1, len(types)):
                    assert order.get(types[i], 99) >= order.get(types[i - 1], 99)
                break
            elif msg["type"] == "done":
                pytest.fail("unexpected done")

    @pytest.mark.asyncio
    async def test_ack_moves_to_next(self, client):
        """ACK 后不重复拉同一 tick."""
        await client.post("/api/world/test/session/start")
        first_tick = None
        while True:
            r = await client.get("/api/world/test/tick/next")
            msg = r.json()
            if msg["type"] == "tick":
                first_tick = msg["data"]["tick"]
                await client.post(f"/api/world/test/tick/{first_tick}/ack")
                break
        # 拉第二条
        while True:
            r = await client.get("/api/world/test/tick/next")
            msg = r.json()
            if msg["type"] == "tick":
                assert msg["data"]["tick"] != first_tick
                break

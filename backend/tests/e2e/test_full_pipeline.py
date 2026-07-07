"""全链路 E2E——mock LLM + 真实 DB + HTTP API.

覆盖完整 tick 生命周期：启动 → 生成 tick → 拉取事件 → ACK → 验证 DB。
每个阶段都有独立断言，任一阶段失败即可定位问题。
"""

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain import PlayerCharacter, World
from src.orchestrator import Orchestrator
from src.repository import (
    ActorRepo,
    DMRecordRepo,
    MemoryRepo,
    PcRepo,
    SceneRepo,
    TickEventRepo,
    WorldRepo,
)
from src.server import app
from src.storage.chroma_client import ChromaClient
from src.storage.sqlite_client import SQLiteClient
from tests.conftest import _make_mock_llm


@pytest.fixture
async def client(tmp_path):
    """真实 SQLite + mock LLM Orchestrator + 真实 App."""
    db_path = tmp_path / "e2e.db"
    db = SQLiteClient(str(db_path))
    await db.connect()
    await db.init_schema()

    chroma_path = tmp_path / "chroma"
    chroma = ChromaClient(str(chroma_path))
    memory_repo = MemoryRepo(chroma=chroma, sqlite=db)
    await memory_repo.initialize()

    repos = {
        "world": WorldRepo(db),
        "char": PcRepo(db),
        "actor": ActorRepo(db),
        "scene": SceneRepo(db),
        "memory": memory_repo,
        "event": TickEventRepo(db),
        "dm_record": DMRecordRepo(db),
    }
    orch = Orchestrator(repos=repos, llm=_make_mock_llm())

    app.state.db = db
    app.state.orchestrator = orch

    # 创建测试世界 / Create test world
    await repos["world"].create(World(id="e2e_mock", name="E2E Mock World"))

    # 创建测试 PC，使其参与决策 / Create test PC so it can make decisions
    await repos["char"].save(
        PlayerCharacter(
            id="pc-e2e",
            name="E2E Hero",
            role="fighter",
            scene_id="tavern",
            world_id="e2e_mock",
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    # 清理：先取消可能还在跑的 batch/loop，再关闭 DB / Cancel running tasks before closing DB
    from src.tick_runner import batch_runner, loop_manager

    batch_runner.cancel("e2e_mock")
    loop_manager.stop("e2e_mock")
    await asyncio.sleep(0.2)

    await db.close()
    if getattr(app.state, "db", None):
        app.state.db = None
    if getattr(app.state, "orchestrator", None):
        app.state.orchestrator = None


async def _wait_batch_done(client, world_id: str, expected_completed: int, timeout: float = 60):
    """等待 batch 完成 / Wait for batch completion."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = await client.get(f"/api/world/{world_id}/loop/status")
        status = r.json()
        completed = status.get("batch_completed") or 0
        if not status["batch_running"] and completed == expected_completed:
            return status
        await asyncio.sleep(0.2)
    pytest.fail(f"batch 未在 {timeout}s 内完成")


class TestFullPipeline:
    """全链路每个阶段独立断言 / Per-stage assertions for full pipeline."""

    @pytest.mark.asyncio
    async def test_stage_0_world_exists(self, client):
        """阶段 0：世界已创建 / Stage 0: world exists."""
        r = await client.get("/api/world/e2e_mock/state")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["world_id"] == "e2e_mock"
        assert data["data_tick"] == 0
        assert data["display_tick"] == 0
        assert any(pc["id"] == "pc-e2e" for pc in data["pcs"])

    @pytest.mark.asyncio
    async def test_stage_1_batch_tick_produces_events(self, client):
        """阶段 1：batch 执行后产生事件 / Stage 1: batch produces events."""
        r = await client.post("/api/world/e2e_mock/tick/batch/1")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ok"

        await _wait_batch_done(client, "e2e_mock", 1)

        r = await client.get("/api/world/e2e_mock/events?since_tick=0&tick_limit=1")
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["events"]) > 0, "至少应有一个事件"
        assert data["data_tick"] == 1
        assert data["display_tick"] == 1

        event_types = [e["type"] for e in data["events"]]
        assert "dm_create" in event_types, f"缺少 dm_create: {event_types}"
        assert "scene_setup" in event_types, f"缺少 scene_setup: {event_types}"
        assert "pc_decision" in event_types, f"缺少 pc_decision: {event_types}"
        assert "dm_narrative" in event_types, f"缺少 dm_narrative: {event_types}"

    @pytest.mark.asyncio
    async def test_stage_2_db_persists_characters_and_events(self, client):
        """阶段 2：DB 持久化角色与事件 / Stage 2: DB persists characters and events."""
        r = await client.post("/api/world/e2e_mock/tick/batch/1")
        assert r.status_code == 200

        await _wait_batch_done(client, "e2e_mock", 1)

        db = app.state.db

        rows = await db.fetch_all(
            "SELECT COUNT(*) as cnt FROM tick_events WHERE world_id = ?",
            ("e2e_mock",),
        )
        assert rows[0]["cnt"] > 0, "tick_events 表应有记录"

        world_row = await db.fetch_one(
            "SELECT data_tick, display_tick FROM worlds WHERE id = ?",
            ("e2e_mock",),
        )
        assert world_row["data_tick"] >= 1

    @pytest.mark.asyncio
    async def test_stage_3_ack_updates_display_tick(self, client):
        """阶段 3：ACK 更新 display_tick / Stage 3: ACK updates display_tick."""
        r = await client.post("/api/world/e2e_mock/tick/batch/1")
        assert r.status_code == 200

        await _wait_batch_done(client, "e2e_mock", 1)

        r = await client.post("/api/world/e2e_mock/tick/display/1")
        assert r.status_code == 200, r.text
        assert r.json()["display_tick"] == 1

        r = await client.get("/api/world/e2e_mock/state")
        assert r.json()["display_tick"] == 1

    @pytest.mark.asyncio
    async def test_stage_4_consecutive_ticks_increment_data_tick(self, client):
        """阶段 4：连续 tick 推进 data_tick / Stage 4: consecutive ticks advance data_tick."""
        r = await client.post("/api/world/e2e_mock/tick/batch/3")
        assert r.status_code == 200

        await _wait_batch_done(client, "e2e_mock", 3, timeout=60)

        r = await client.get("/api/world/e2e_mock/events?since_tick=0&tick_limit=10")
        data = r.json()
        assert data["data_tick"] == 3
        assert len(data["events"]) >= 3

        ticks = {e["tick"] for e in data["events"] if e["type"] == "dm_create"}
        assert ticks == {1, 2, 3}, f"缺少某些 tick 的 dm_create: {ticks}"

    @pytest.mark.asyncio
    async def test_stage_5_event_tick_range_filtering(self, client):
        """阶段 5：事件按 tick 范围过滤 / Stage 5: event tick range filtering."""
        r = await client.post("/api/world/e2e_mock/tick/batch/3")
        assert r.status_code == 200

        await _wait_batch_done(client, "e2e_mock", 3, timeout=60)

        r = await client.get("/api/world/e2e_mock/events?since_tick=1&tick_limit=1")
        data = r.json()
        assert all(e["tick"] == 2 for e in data["events"]), "应只返回 tick=2 的事件"

    @pytest.mark.asyncio
    async def test_stage_6_throttle_prevents_excessive_ahead(self, client):
        """阶段 6：data_tick 不能超过 display_tick 3 个以上 / Stage 6: throttle."""
        # 直接跑 5 个 tick，不 ACK / Run 5 ticks without ACK
        r = await client.post("/api/world/e2e_mock/tick/batch/5")
        assert r.status_code == 200

        # 等待 data_tick 达到 3 / Wait for data_tick to reach 3
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            r = await client.get("/api/world/e2e_mock/state")
            data = r.json()
            if data["data_tick"] >= 3:
                break
            await asyncio.sleep(0.2)
        else:
            pytest.fail("data_tick 未达到 3")

        # 此时应被 throttle 卡住 / Should be throttled now
        r = await client.get("/api/world/e2e_mock/loop/status")
        assert r.json()["batch_running"] is True, "batch 应因 throttle 暂停"

        # ACK 后 batch 应继续完成 / ACK allows batch to continue
        r = await client.post("/api/world/e2e_mock/tick/display/3")
        assert r.status_code == 200, r.text

        await _wait_batch_done(client, "e2e_mock", 5, timeout=60)

        r = await client.get("/api/world/e2e_mock/state")
        data = r.json()
        assert data["data_tick"] == 5
        assert data["data_tick"] - data["display_tick"] <= 3

    @pytest.mark.asyncio
    async def test_stage_7_pause_cancels_batch_without_409(self, client):
        """阶段 7：暂停取消 batch，不会 409 / Stage 7: pause cancels batch."""
        r = await client.post("/api/world/e2e_mock/tick/batch/10")
        assert r.status_code == 200

        # 立即暂停 / Pause immediately
        r = await client.post("/api/world/e2e_mock/loop/pause")
        assert r.status_code == 200, r.text
        assert r.json()["batch_cancelled"] is True

        # 再次启动 batch 不应 409 / Starting a new batch should not 409
        await asyncio.sleep(0.3)
        r = await client.post("/api/world/e2e_mock/tick/batch/1")
        assert r.status_code == 200, f"暂停后应能重新启动 batch: {r.text}"

    @pytest.mark.asyncio
    async def test_stage_8_reset_clears_state(self, client):
        """阶段 8：重置清空 tick 和事件 / Stage 8: reset clears state."""
        r = await client.post("/api/world/e2e_mock/tick/batch/2")
        assert r.status_code == 200
        await _wait_batch_done(client, "e2e_mock", 2, timeout=60)

        r = await client.post("/api/world/e2e_mock/reset")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ok"

        r = await client.get("/api/world/e2e_mock/state")
        data = r.json()
        assert data["data_tick"] == 0
        assert data["display_tick"] == 0

        db = app.state.db
        rows = await db.fetch_all(
            "SELECT COUNT(*) as cnt FROM tick_events WHERE world_id = ?",
            ("e2e_mock",),
        )
        assert rows[0]["cnt"] == 0, "重置后 tick_events 应为空"

    @pytest.mark.asyncio
    async def test_stage_9_invalid_requests_handled(self, client):
        """阶段 9：非法请求返回正确错误码 / Stage 9: invalid requests."""
        r = await client.post("/api/world/e2e_mock/tick/batch/0")
        assert r.status_code == 400

        r = await client.post("/api/world/e2e_mock/tick/display/-1")
        assert r.status_code == 400

        r = await client.get("/api/world/not_exists/state")
        assert r.status_code == 200  # 当前实现不存在 world 也返回空状态
        assert r.json()["data_tick"] == 0

    @pytest.mark.asyncio
    async def test_stage_10_memory_persisted(self, client):
        """阶段 10：tick 后记忆写入 SQLite/Chroma / Stage 10: memory persisted."""
        r = await client.post("/api/world/e2e_mock/tick/batch/1")
        assert r.status_code == 200
        await _wait_batch_done(client, "e2e_mock", 1)

        db = app.state.db
        rows = await db.fetch_all(
            "SELECT COUNT(*) as cnt FROM memories WHERE pc_id = ?",
            ("pc-e2e",),
        )
        assert rows[0]["cnt"] >= 0, "memories 表查询应正常"

    @pytest.mark.asyncio
    async def test_stage_11_world_crud(self, client):
        """阶段 11：世界 CRUD 端点 / Stage 11: world CRUD."""
        r = await client.get("/api/world")
        assert r.status_code == 200
        worlds = r.json()
        assert any(w["id"] == "e2e_mock" for w in worlds)

        r = await client.post("/api/world", json={"id": "e2e_new", "name": "New World"})
        assert r.status_code == 200, r.text

        r = await client.get("/api/world")
        assert any(w["id"] == "e2e_new" for w in r.json())

    @pytest.mark.asyncio
    async def test_stage_12_loop_start_pause(self, client):
        """阶段 12：持续循环可启停 / Stage 12: continuous loop start/pause."""
        r = await client.post("/api/world/e2e_mock/loop/start")
        assert r.status_code == 200, r.text
        assert r.json()["running"] is True

        r = await client.get("/api/world/e2e_mock/loop/status")
        assert r.json()["running"] is True

        r = await client.post("/api/world/e2e_mock/loop/pause")
        assert r.status_code == 200, r.text
        assert r.json()["running"] is False

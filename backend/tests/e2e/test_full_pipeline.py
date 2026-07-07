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

    await db.close()
    if getattr(app.state, "db", None):
        app.state.db = None
    if getattr(app.state, "orchestrator", None):
        app.state.orchestrator = None


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
        # 启动 batch / Start batch
        r = await client.post("/api/world/e2e_mock/tick/batch/1")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ok"

        # 等待 batch 完成 / Wait for batch completion
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            r = await client.get("/api/world/e2e_mock/loop/status")
            status = r.json()
            if not status["batch_running"] and status["batch_completed"] == 1:
                break
            await asyncio.sleep(0.2)
        else:
            pytest.fail("batch 未在 30s 内完成")

        # 拉取事件 / Pull events
        r = await client.get("/api/world/e2e_mock/events?since_tick=0&tick_limit=1")
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["events"]) > 0, "至少应有一个事件"
        assert data["data_tick"] == 1
        assert data["display_tick"] == 1

        # 验证关键事件阶段 / Verify key event phases
        event_types = [e["type"] for e in data["events"]]
        assert "dm_create" in event_types, f"缺少 dm_create: {event_types}"
        assert "scene_setup" in event_types, f"缺少 scene_setup: {event_types}"
        assert "pc_decision" in event_types, f"缺少 pc_decision: {event_types}"
        assert "dm_narrative" in event_types, f"缺少 dm_narrative: {event_types}"

    @pytest.mark.asyncio
    async def test_stage_2_db_persists_characters_and_events(self, client):
        """阶段 2：DB 持久化角色与事件 / Stage 2: DB persists characters and events."""
        # 先执行一个 tick / Run one tick first
        r = await client.post("/api/world/e2e_mock/tick/batch/1")
        assert r.status_code == 200

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            r = await client.get("/api/world/e2e_mock/loop/status")
            status = r.json()
            if not status["batch_running"]:
                break
            await asyncio.sleep(0.2)

        db = app.state.db

        # 验证 tick_events 表 / Verify tick_events table
        rows = await db.fetch_all(
            "SELECT COUNT(*) as cnt FROM tick_events WHERE world_id = ?",
            ("e2e_mock",),
        )
        assert rows[0]["cnt"] > 0, "tick_events 表应有记录"

        # 验证 worlds 表 tick 推进 / Verify worlds tick advanced
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

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            r = await client.get("/api/world/e2e_mock/loop/status")
            if not r.json()["batch_running"]:
                break
            await asyncio.sleep(0.2)

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

        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            r = await client.get("/api/world/e2e_mock/loop/status")
            status = r.json()
            if not status["batch_running"] and status["batch_completed"] == 3:
                break
            await asyncio.sleep(0.2)
        else:
            pytest.fail("3-tick batch 未在 60s 内完成")

        r = await client.get("/api/world/e2e_mock/events?since_tick=0&tick_limit=10")
        data = r.json()
        assert data["data_tick"] == 3
        assert len(data["events"]) >= 3

        # 每个 tick 都有 dm_create / Each tick has dm_create
        ticks = {e["tick"] for e in data["events"] if e["type"] == "dm_create"}
        assert ticks == {1, 2, 3}, f"缺少某些 tick 的 dm_create: {ticks}"

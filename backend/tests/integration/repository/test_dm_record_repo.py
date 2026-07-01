"""DMRecordRepo 集成测试 / Integration tests for DM Record Repository——真实 SQLite DB 读写."""

import pytest

# 测试 save_plot_brief/update_narrative/load_range/load_summaries 等所有方法
# 测试 save/update/load 全链路 + StorySummary 读写
# 用法: pytest tests/integration/repository/test_dm_record_repo.py -v
# 验证 UNIQUE(world_id,tick_start) 去重
from src.domain.dm_record import DMRecord
from src.domain.story_summary import StorySummary
from src.repository.dm_record_repo import DMRecordRepo
from src.storage.sqlite_client import SQLiteClient


@pytest.fixture
async def db():
    client = SQLiteClient(":memory:")
    await client.connect()
    await client.init_schema()
    yield client


@pytest.fixture
async def repo(db):
    return DMRecordRepo(db)


class TestDMRecord:
    @pytest.mark.asyncio
    async def test_save_plot_brief_and_update_narrative(self, repo):
        await repo.save_plot_brief(DMRecord(world_id="test", tick=0, plot_brief="场景A"))
        await repo.update_narrative(DMRecord(world_id="test", tick=0, dm_narrative="叙事A"))
        rows = await repo.load_by_world("test")
        assert len(rows) == 1
        assert rows[0].plot_brief == "场景A"
        assert rows[0].dm_narrative == "叙事A"

    @pytest.mark.asyncio
    async def test_save_plot_brief_updates_existing(self, repo):
        await repo.save_plot_brief(DMRecord(world_id="test", tick=1, plot_brief="v1"))
        await repo.save_plot_brief(DMRecord(world_id="test", tick=1, plot_brief="v2"))
        rows = await repo.load_by_world("test")
        assert len(rows) == 1
        assert rows[0].plot_brief == "v2"

    @pytest.mark.asyncio
    async def test_load_empty(self, repo):
        rows = await repo.load_by_world("test")
        assert rows == []

    @pytest.mark.asyncio
    async def test_load_ordered_by_tick_asc(self, repo):
        for i in range(5):
            await repo.save_plot_brief(DMRecord(world_id="test", tick=i, plot_brief="p"))
            await repo.update_narrative(DMRecord(world_id="test", tick=i, dm_narrative="n"))
        rows = await repo.load_by_world("test")
        assert [r.tick for r in rows] == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_load_respects_limit(self, repo):
        for i in range(20):
            await repo.save_plot_brief(DMRecord(world_id="test", tick=i, plot_brief="p"))
            await repo.update_narrative(DMRecord(world_id="test", tick=i, dm_narrative="n"))
        rows = await repo.load_by_world("test", limit=10)
        assert len(rows) == 10
        assert rows[0].tick == 10
        assert rows[-1].tick == 19

    @pytest.mark.asyncio
    async def test_load_range(self, repo):
        for i in range(5):
            await repo.save_plot_brief(DMRecord(world_id="test", tick=i, plot_brief="p"))
            await repo.update_narrative(DMRecord(world_id="test", tick=i, dm_narrative="n"))
        rows = await repo.load_range("test", 1, 3)
        assert len(rows) == 3
        assert [r.tick for r in rows] == [1, 2, 3]


class TestStorySummary:
    @pytest.mark.asyncio
    async def test_insert_and_load(self, repo):
        s = StorySummary(world_id="test", tick_start=1, tick_end=10, summary="章节摘要")
        await repo.insert_summary(s)
        summaries = await repo.load_summaries("test")
        assert len(summaries) == 1
        assert summaries[0].summary == "章节摘要"

    @pytest.mark.asyncio
    async def test_replace_same_range(self, repo):
        await repo.insert_summary(
            StorySummary(world_id="test", tick_start=1, tick_end=10, summary="v1")
        )
        await repo.insert_summary(
            StorySummary(world_id="test", tick_start=1, tick_end=10, summary="v2")
        )
        summaries = await repo.load_summaries("test")
        assert len(summaries) == 1
        assert summaries[0].summary == "v2"

    @pytest.mark.asyncio
    async def test_load_empty(self, repo):
        assert await repo.load_summaries("test") == []

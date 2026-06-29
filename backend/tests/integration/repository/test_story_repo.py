"""StoryRepo 集成测试——真实 SQLite DB 读写 / Integration tests for StoryRepo with real SQLite."""
import pytest

from src.domain import StoryArc, StoryHook
from src.repository.story_repo import StoryRepo
from src.storage.sqlite_client import SQLiteClient


@pytest.fixture
async def db():
    client = SQLiteClient(":memory:")
    await client.connect()
    await client.init_schema()
    yield client


@pytest.fixture
async def story_repo(db):
    return StoryRepo(db)


class TestStoryArc:
    @pytest.mark.asyncio
    async def test_save_and_load_arc(self, story_repo):
        arc = StoryArc(id="arc_test1", type="main", title="Test Arc", stage="铺陈")
        await story_repo.save_arc(arc)
        arcs = await story_repo.load_arcs()
        assert len(arcs) == 1
        assert arcs[0].id == "arc_test1"
        assert arcs[0].type == "main"
        assert arcs[0].title == "Test Arc"

    @pytest.mark.asyncio
    async def test_save_arc_updates_existing(self, story_repo):
        arc = StoryArc(id="arc_test1", title="Original", stage="铺陈")
        await story_repo.save_arc(arc)
        arc.title = "Updated"
        arc.stage = "发展"
        await story_repo.save_arc(arc)
        arcs = await story_repo.load_arcs()
        assert len(arcs) == 1
        assert arcs[0].title == "Updated"
        assert arcs[0].stage == "发展"

    @pytest.mark.asyncio
    async def test_load_arcs_empty(self, story_repo):
        arcs = await story_repo.load_arcs()
        assert arcs == []

    @pytest.mark.asyncio
    async def test_save_arc_with_cast_and_branch_points(self, story_repo):
        arc = StoryArc(
            id="arc_test2",
            type="side",
            title="Side Arc",
            main_cast=["alex"],
            supporting_actors=["innkeeper"],
        )
        await story_repo.save_arc(arc)
        arcs = await story_repo.load_arcs()
        assert arcs[0].main_cast == ["alex"]
        assert arcs[0].supporting_actors == ["innkeeper"]


class TestStoryHook:
    @pytest.mark.asyncio
    async def test_save_and_load_hook(self, story_repo):
        hook = StoryHook(
            id="hook_test1",
            planted_tick=3,
            description="A mysterious letter arrives.",
            intended_payoff="Reveal the sender's identity",
        )
        await story_repo.save_hook(hook)
        hooks = await story_repo.load_hooks()
        assert len(hooks) == 1
        assert hooks[0].id == "hook_test1"
        assert hooks[0].status == "planted"

    @pytest.mark.asyncio
    async def test_resolve_hook_changes_status(self, story_repo):
        hook = StoryHook(id="hook_test1", planted_tick=0, description="Clue")
        await story_repo.save_hook(hook)
        hook.status = "resolved"
        await story_repo.save_hook(hook)
        hooks = await story_repo.load_hooks()
        assert hooks[0].status == "resolved"

    @pytest.mark.asyncio
    async def test_load_hooks_empty(self, story_repo):
        hooks = await story_repo.load_hooks()
        assert hooks == []


class TestNarrative:
    @pytest.mark.asyncio
    async def test_insert_narrative(self, story_repo, db):
        await story_repo.insert_narrative(tick=0, content="The world awakens...")
        rows = await db.fetch_all("SELECT * FROM narratives")
        assert len(rows) == 1
        assert rows[0]["tick"] == 0

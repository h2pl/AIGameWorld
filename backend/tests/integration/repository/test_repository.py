"""Repository 集成测试——真实 SQLite DB 读写."""
import pytest

from src.storage.sqlite_client import SQLiteClient
from src.repository.character_repo import CharacterRepo
from src.repository.event_repo import EventRepo
from src.domain.character import PlayerCharacter, Actor, Location
from src.domain.event import Event


@pytest.fixture
async def db():
    client = SQLiteClient(":memory:")
    await client.connect()
    await client.init_schema()
    yield client


@pytest.fixture
async def char_repo(db):
    return CharacterRepo(db)


@pytest.fixture
async def event_repo(db):
    return EventRepo(db)


class TestCharacterRepo:
    @pytest.mark.asyncio
    async def test_save_and_load_pc(self, char_repo):
        pc = PlayerCharacter(id="pc_test1", name="Hero")
        await char_repo.save_pc(pc)
        pcs = await char_repo.load_pcs()
        assert len(pcs) == 1
        assert pcs[0].id == "pc_test1"
        assert pcs[0].name == "Hero"

    @pytest.mark.asyncio
    async def test_save_pc_updates_existing(self, char_repo):
        pc = PlayerCharacter(id="pc_test2", name="Hero", status="active")
        await char_repo.save_pc(pc)

        pc.status = "injured"
        pc.location = Location(scene_id="forest_01")
        await char_repo.save_pc(pc)

        pcs = await char_repo.load_pcs()
        assert pcs[0].status == "injured"
        assert pcs[0].location.scene_id == "forest_01"

    @pytest.mark.asyncio
    async def test_save_and_load_actor(self, char_repo):
        actor = Actor(id="npc_test1", name="Guard", role="guard")
        await char_repo.save_actor(actor)
        actors = await char_repo.load_actors()
        assert len(actors) == 1
        assert actors[0].id == "npc_test1"

    @pytest.mark.asyncio
    async def test_save_actor_updates_existing(self, char_repo):
        actor = Actor(id="npc_test2", name="Vendor")
        await char_repo.save_actor(actor)

        actor.dm_assigned = True
        actor.motivation_injected = "protect the village"
        await char_repo.save_actor(actor)

        actors = await char_repo.load_actors()
        assert actors[0].dm_assigned is True
        assert actors[0].motivation_injected == "protect the village"

    @pytest.mark.asyncio
    async def test_multiple_characters(self, char_repo):
        await char_repo.save_pc(PlayerCharacter(id="pc_a", name="Alice"))
        await char_repo.save_pc(PlayerCharacter(id="pc_b", name="Bob"))
        await char_repo.save_actor(Actor(id="npc_a", name="Carol"))

        pcs = await char_repo.load_pcs()
        actors = await char_repo.load_actors()
        assert len(pcs) == 2
        assert len(actors) == 1


class TestEventRepo:
    @pytest.mark.asyncio
    async def test_insert_and_load(self, event_repo):
        evt = Event(id="evt_1", tick=0, type="combat", data={"damage": 10})
        await event_repo.insert(evt)
        events = await event_repo.load_all()
        assert len(events) == 1
        assert events[0].type == "combat"
        assert events[0].data["damage"] == 10

    @pytest.mark.asyncio
    async def test_load_empty(self, event_repo):
        events = await event_repo.load_all()
        assert events == []

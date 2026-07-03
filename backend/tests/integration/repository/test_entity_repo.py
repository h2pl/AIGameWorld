"""Repository 集成测试——内存 SQLite 验证 TickMessageRepo / TickEventRepo / CharacterRepo 读写."""

import pytest

from src.domain.actor import Actor
from src.domain.event import Event
from src.domain.message import Message
from src.domain.player_character import PlayerCharacter
from src.repository.character_repo import CharacterRepo
from src.repository.event_repo import TickEventRepo
from src.repository.message_repo import TickMessageRepo
from src.storage.sqlite_client import SQLiteClient

# ══ Fixtures / 夹具 ══


@pytest.fixture
async def db():
    """内存 SQLite / In-memory SQLite."""
    client = SQLiteClient(":memory:")
    await client.connect()
    await client.init_schema()
    yield client


@pytest.fixture
async def char_repo(db):
    return CharacterRepo(db)


@pytest.fixture
async def event_repo(db):
    return TickEventRepo(db)


@pytest.fixture
async def msg_repo(db):
    return TickMessageRepo(db)


# ══ CharacterRepo 测试 / Character Repo Tests ══


class TestCharacterRepo:
    # 保存并加载 PC / Save and load PC
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
        pc.scene_id = "forest_01"
        await char_repo.save_pc(pc)

        pcs = await char_repo.load_pcs()
        assert pcs[0].status == "injured"
        assert pcs[0].scene_id == "forest_01"

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


class TestMessageEventRepo:
    """Message + Event 联合测试 / Combined Message + Event tests."""

    # 辅助：插入测试消息 / Helper: insert test msg
    async def _insert_msg(self, msg_repo, mid="aw_test", tick=1):
        msg = Message(id=mid, tick=tick, world_id="test", timestamp="2026-07-01T12:00:00Z")
        await msg_repo.insert(msg)
        await msg_repo.mark_ready(mid, tick)

    @pytest.mark.asyncio
    async def test_insert_and_load_events(self, msg_repo, event_repo):
        await self._insert_msg(msg_repo)
        evts = [
            Event(type="dm_narrative", tick=1, payload={"text": "Hello world"}),
            Event(type="character_talk", tick=1, payload={"character_id": "fighter", "text": "Hi"}),
        ]
        await event_repo.insert_events("aw_test", 1, evts)
        loaded = await event_repo.load_by_message("aw_test", 1)
        assert len(loaded) == 2
        # character_talk (SEQUENCE idx=2) 排在 dm_narrative (idx=4) 前面
        assert loaded[0].payload["character_id"] == "fighter"
        assert loaded[1].payload["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_load_empty_events(self, event_repo):
        loaded = await event_repo.load_by_message("nonexistent", 0)
        assert loaded == []

    @pytest.mark.asyncio
    async def test_events_ordered_by_seq(self, msg_repo, event_repo):
        await self._insert_msg(msg_repo)
        evts = [
            Event(type="dm_narrative", tick=1, payload={"text": "first"}),
            Event(type="dm_narrative", tick=1, payload={"text": "second"}),
            Event(type="dm_narrative", tick=1, payload={"text": "third"}),
        ]
        await event_repo.insert_events("aw_test", 1, evts)
        loaded = await event_repo.load_by_message("aw_test", 1)
        assert loaded[0].payload["text"] == "first"
        assert loaded[1].payload["text"] == "second"
        assert loaded[2].payload["text"] == "third"

    @pytest.mark.asyncio
    async def test_insert_then_get_pending(self, msg_repo, event_repo):
        msg = Message(
            id="aw_test",
            tick=1,
            world_id="test",
            timestamp="2026-07-01T12:00:00Z",
        )
        await msg_repo.insert(msg)
        evt = Event(type="dm_narrative", tick=1, payload={"text": "test"})
        await event_repo.insert_events(msg.id, msg.tick, [evt])
        await msg_repo.mark_ready(msg.id, msg.tick)
        meta = await msg_repo.get_next_pending("aw_test")
        assert meta is not None
        assert meta["tick"] == 1
        events = await event_repo.load_by_message(meta["id"], meta["tick"])
        assert len(events) == 1
        assert events[0].payload["text"] == "test"

    @pytest.mark.asyncio
    async def test_ack_skips_consumed(self, msg_repo):
        await self._insert_msg(msg_repo, tick=1)
        await self._insert_msg(msg_repo, tick=2)
        await msg_repo.ack("aw_test", 1)
        meta = await msg_repo.get_next_pending("aw_test")
        assert meta["tick"] == 2

    @pytest.mark.asyncio
    async def test_get_pending_empty(self, msg_repo):
        meta = await msg_repo.get_next_pending("no_session")
        assert meta is None

    @pytest.mark.asyncio
    async def test_ack_all_then_none(self, msg_repo):
        await self._insert_msg(msg_repo, tick=1)
        await msg_repo.ack("aw_test", 1)
        meta = await msg_repo.get_next_pending("aw_test")
        assert meta is None

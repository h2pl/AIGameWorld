"""Test storage layer – M1-3 / M1-4 / M1-5."""

import tempfile
from pathlib import Path

import pytest

from src.models import (
    Actor,
    Attributes,
    CharacterArc,
    CombatStats,
    Equipment,
    Event,
    InventorySlot,
    Item,
    ItemType,
    Location,
    MainCastRoster,
    PlayerCharacter,
    Relationship,
    Scene,
    SceneObject,
    SceneObjectType,
    StoryArc,
    StoryHook,
    WorldState,
)
from src.storage import ChromaManager, CheckpointStore, WorldStateStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_world.db"
        yield db_path


@pytest.fixture
def temp_chroma():
    """Create a temporary ChromaDB directory for testing."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield Path(tmpdir)


async def _seed_scene(store: WorldStateStore, scene_id: str = "village") -> None:
    """Insert a scene row so FK constraints are satisfied."""
    await store._db.execute(
        "INSERT OR IGNORE INTO scenes (id, name, type, pack_name) VALUES (?, ?, ?, ?)",
        (scene_id, "Test Scene", "village", "forgotten_realms"),
    )
    await store._db.commit()


# ---- PlayerCharacter / Actor fixture helpers ----

def make_pc(name: str, role: str = "fighter") -> PlayerCharacter:
    return PlayerCharacter(
        id=name.lower(),
        name=name,
        role=role,
        location=Location(scene_id="village", position_x=1, position_y=2),
        attributes=Attributes(strength=16, dexterity=12, constitution=14),
        combat=CombatStats(hp=30, max_hp=30, ac=16),
        character_arc=CharacterArc(growth_line="test arc"),
        values=["justice"],
        equipment=Equipment(weapon="longsword"),
        inventory=[InventorySlot(item_id="health_potion", qty=2)],
        relationships={"elara": Relationship(trust=0.5, interaction_count=3)},
        joined_tick=0,
    )


def make_actor(name: str, role: str = "blacksmith") -> Actor:
    return Actor(
        id=name.lower(),
        name=name,
        role=role,
        location=Location(scene_id="village", position_x=3, position_y=4),
        attributes=Attributes(strength=14, dexterity=10),
        combat=CombatStats(hp=20, max_hp=20, ac=14),
        functions=["merchant", "dialogue"],
        function_data={"merchant": {"gold": 500}},
    )


def make_event(tick: int = 1, seq: int = 0) -> Event:
    return Event(id=f"evt_{tick}_{seq}", tick=tick, seq=seq, type="test_event")


# === Test Classes / 测试类 ===
# === Test Class / 测试类 ===
class TestWorldStateStore:
    async def test_init_creates_tables(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        try:
            rows = await store._db.execute_fetchall(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            names = {row[0] for row in rows}
            expected = {
                "schema_version", "world_meta",
                "player_characters", "actors", "main_cast",
                "scenes", "items", "scene_objects",
                "story_arcs", "story_hooks",
                "events", "narratives", "quests", "factions",
            }
            assert expected.issubset(names)
        finally:
            await store.close()

    async def test_save_and_load_pcs(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        await _seed_scene(store)
        try:
            kael = make_pc("Kael", "fighter")
            zeph = make_pc("Zeph", "rogue")
            state = WorldState(
                tick=3,
                current_world="forgotten_realms",
                current_scene="village",
                player_characters={"kael": kael, "zeph": zeph},
            )
            await store.save_tick(state, [])
            loaded = await store.load_world_state()
            assert loaded.tick == 3
            assert loaded.player_characters["kael"].name == "Kael"
            assert loaded.player_characters["kael"].equipment.weapon == "longsword"
            assert loaded.player_characters["zeph"].role == "rogue"
        finally:
            await store.close()

    async def test_save_and_load_actors(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        await _seed_scene(store)
        try:
            garret = make_actor("Garret")
            state = WorldState(actors={"garret": garret})
            await store.save_tick(state, [])
            loaded = await store.load_world_state()
            assert loaded.actors["garret"].name == "Garret"
            assert loaded.actors["garret"].function_data["merchant"]["gold"] == 500
        finally:
            await store.close()

    async def test_pc_upsert_updates_fields(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        await _seed_scene(store)
        try:
            kael = make_pc("Kael")
            state = WorldState(player_characters={"kael": kael})
            await store.save_tick(state, [])
            kael.combat.hp = 15  # wounded
            state.tick = 2
            await store.save_tick(state, [])
            loaded = await store.load_world_state()
            assert loaded.player_characters["kael"].combat.hp == 15
            assert loaded.tick == 2
        finally:
            await store.close()

    async def test_save_with_events(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        try:
            state = WorldState(tick=1)
            events = [make_event(1, 0), make_event(1, 1)]
            await store.save_tick(state, events)
            loaded = await store.load_world_state()
            assert len(loaded.event_log) == 0  # events not loaded by default
        finally:
            await store.close()

    async def test_save_with_narrative(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        try:
            state = WorldState(tick=1)
            await store.save_tick(state, [], narrative="The village awakens.")
            rows = await store._db.execute_fetchall("SELECT * FROM narratives")
            assert len(rows) == 1
            assert rows[0]["content"] == "The village awakens."
        finally:
            await store.close()

    async def test_load_scenes(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        try:
            await store._db.execute(
                "INSERT INTO scenes (id, name, type, pack_name) VALUES (?, ?, ?, ?)",
                ("village", "Elderwood", "village", "forgotten_realms"),
            )
            await store._db.commit()
            loaded = await store.load_world_state()
            assert loaded.scenes["village"].name == "Elderwood"
        finally:
            await store.close()

    async def test_load_items(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        try:
            await store._db.execute(
                "INSERT INTO items (id, name, item_type, pack_name) VALUES (?, ?, ?, ?)",
                ("longsword", "Longsword", "weapon", "forgotten_realms"),
            )
            await store._db.commit()
            loaded = await store.load_world_state()
            assert loaded.items["longsword"].name == "Longsword"
        finally:
            await store.close()

    async def test_load_story(self, temp_db):
        store = WorldStateStore(temp_db)
        await store.init()
        try:
            await store._db.execute(
                "INSERT INTO story_arcs (id, type, title) VALUES (?, ?, ?)",
                ("arc_1", "main", "Test Arc"),
            )
            await store._db.execute(
                "INSERT INTO story_hooks (id, planted_tick, description) VALUES (?, ?, ?)",
                ("hook_1", 0, "A stranger passes by"),
            )
            await store._db.commit()
            loaded = await store.load_world_state()
            assert len(loaded.story_arcs) == 1
            assert loaded.story_arcs[0].title == "Test Arc"
            assert len(loaded.story_hooks) == 1
        finally:
            await store.close()

    async def test_transaction_atomicity(self, temp_db):
        """save_tick should roll back on partial failure (simulated by bad data)."""
        store = WorldStateStore(temp_db)
        await store.init()
        try:
            state = WorldState(tick=1)
            bad_event = Event(id="evt_1_0", tick=1, seq=0, type="test", data={"bad": object()})
            with pytest.raises(Exception):
                await store.save_tick(state, [bad_event])
            meta = await store._db.execute_fetchall(
                "SELECT value FROM world_meta WHERE key='tick'"
            )
            assert not meta or meta[0][0] == "0"  # tick not advanced
        finally:
            await store.close()


# === Test Class / 测试类 ===
class TestChromaManager:
    def test_lore_collection_creation(self, temp_chroma):
        mgr = ChromaManager(temp_chroma)
        col = mgr.lore_collection("forgotten_realms")
        assert col.name == "lore_forgotten_realms"

    def test_add_and_query_memory(self, temp_chroma):
        mgr = ChromaManager(temp_chroma)
        mgr.add_memory("kael", "mem_1", "Kael fought a bandit and was wounded.", {"tick": 1, "importance": 3})
        mgr.add_memory("kael", "mem_2", "Kael visited the blacksmith.", {"tick": 2, "importance": 1})
        results = mgr.query_memory("kael", "bandit fight", top_k=5)
        assert len(results) > 0

    def test_memory_isolation(self, temp_chroma):
        """A character's memories should not be retrievable by another."""
        mgr = ChromaManager(temp_chroma)
        mgr.add_memory("kael", "mem_k1", "Kael memory.", {"tick": 1, "importance": 3})
        mgr.add_memory("zeph", "mem_z1", "Zeph memory.", {"tick": 1, "importance": 3})
        k_results = mgr.query_memory("kael", "memory", top_k=5)
        z_results = mgr.query_memory("zeph", "memory", top_k=5)
        k_texts = {r["text"] for r in k_results}
        z_texts = {r["text"] for r in z_results}
        assert "Kael memory." in k_texts
        assert "Zeph memory." in z_texts
        assert "Zeph memory." not in k_texts

    def test_reflection_collection(self, temp_chroma):
        mgr = ChromaManager(temp_chroma)
        mgr.add_reflection("kael", "r1", "Kael feels stronger after the battle.", {"tick": 5, "importance": 4})
        results = mgr.query_reflections("kael", "stronger", top_k=3)
        assert len(results) > 0

    def test_drop_character_cleans_collections(self, temp_chroma):
        mgr = ChromaManager(temp_chroma)
        mgr.add_memory("kael", "mem_1", "test", {"tick": 1})
        mgr.add_reflection("kael", "r1", "test reflection", {"tick": 1})
        mgr.drop_character("kael")
        results = mgr.query_memory("kael", "test")
        assert len(results) == 0

    def test_drop_pack_cleans_lore_and_dm(self, temp_chroma):
        mgr = ChromaManager(temp_chroma)
        lore = mgr.lore_collection("test_pack")
        lore.add(ids=["l1"], documents=["Lore entry"], metadatas=[{"source": "test"}])
        dm_n = mgr.dm_narrative_collection("test_pack")
        dm_n.add(ids=["n1"], documents=["Narrative"], metadatas=[{"tick": 0}])
        dm_s = mgr.dm_summary_collection("test_pack")
        dm_s.add(ids=["s1"], documents=["Summary"], metadatas=[{"tick": 0}])
        mgr.drop_pack("test_pack")
        # After deletion, query on a new empty collection returns empty
        results = mgr.query_lore("test_pack", "Lore")
        assert len(results) == 0


# === Test Class / 测试类 ===
class TestCheckpointStore:
    def test_config_generation(self):
        store = CheckpointStore()
        config = store.get_config("thread_1", "tick_1")
        assert config["configurable"]["thread_id"] == "thread_1"
        assert config["configurable"]["checkpoint_id"] == "tick_1"
        assert "checkpoint_ns" in config["configurable"]

    def test_saver_is_initialized(self):
        store = CheckpointStore()
        assert store.saver is not None

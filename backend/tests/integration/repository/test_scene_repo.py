"""SceneRepo 集成测试 / Integration tests for Scene Repository."""

import pytest

from src.domain import Scene, SceneObject, SceneObjectType
from src.repository.scene_repo import SceneRepo
from src.storage.sqlite_client import SQLiteClient


@pytest.fixture
async def db():
    client = SQLiteClient(":memory:")
    await client.connect()
    await client.init_schema()
    yield client


@pytest.fixture
async def repo(db):
    return SceneRepo(db)


class TestSceneRepo:
    @pytest.mark.asyncio
    async def test_save_and_get_scene(self, repo):
        scene = Scene(
            id="scene-1",
            name="Tavern",
            type="indoor",
            description="一个热闹的酒馆。",
            world_id="world-1",
        )
        await repo.save_scene(scene, "world-1")
        loaded = await repo.get_scene("scene-1")
        assert loaded is not None
        assert loaded.id == "scene-1"
        assert loaded.name == "Tavern"
        assert loaded.type == "indoor"

    @pytest.mark.asyncio
    async def test_get_scene_returns_none_when_missing(self, repo):
        loaded = await repo.get_scene("missing")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_list_scenes_by_world(self, repo):
        await repo.save_scene(Scene(id="s1", name="A", world_id="w1"), "w1")
        await repo.save_scene(Scene(id="s2", name="B", world_id="w1"), "w1")
        await repo.save_scene(Scene(id="s3", name="C", world_id="w2"), "w2")
        scenes = await repo.list_scenes("w1")
        assert len(scenes) == 2
        assert {s.id for s in scenes} == {"s1", "s2"}

    @pytest.mark.asyncio
    async def test_save_object_and_get_object_ids(self, repo):
        await repo.save_scene(Scene(id="scene-1", name="A", world_id="w1"), "w1")
        obj = SceneObject(
            id="obj-1",
            name="Chest",
            object_type=SceneObjectType.CONTAINER,
            scene_id="scene-1",
            world_id="w1",
        )
        await repo.save_object(obj)
        ids = await repo.get_object_ids("scene-1")
        assert ids == ["obj-1"]

    @pytest.mark.asyncio
    async def test_get_object_ids_empty_when_scene_has_no_objects(self, repo):
        await repo.save_scene(Scene(id="scene-1", name="A", world_id="w1"), "w1")
        ids = await repo.get_object_ids("scene-1")
        assert ids == []

    @pytest.mark.asyncio
    async def test_list_objects_by_world(self, repo):
        await repo.save_scene(Scene(id="scene-1", name="A", world_id="w1"), "w1")
        await repo.save_object(
            SceneObject(
                id="obj-1",
                name="Chest",
                object_type=SceneObjectType.CONTAINER,
                scene_id="scene-1",
                world_id="w1",
            )
        )
        objects = await repo.list_objects_by_world("w1")
        assert len(objects) == 1
        assert objects[0]["id"] == "obj-1"
        assert objects[0]["scene_id"] == "scene-1"

    @pytest.mark.asyncio
    async def test_delete_by_world_cascades(self, repo):
        await repo.save_scene(Scene(id="scene-1", name="A", world_id="w1"), "w1")
        await repo.save_object(
            SceneObject(
                id="obj-1",
                name="Chest",
                object_type=SceneObjectType.CONTAINER,
                scene_id="scene-1",
                world_id="w1",
            )
        )
        await repo.delete_by_world("w1")
        assert await repo.get_scene("scene-1") is None
        assert await repo.get_object_ids("scene-1") == []

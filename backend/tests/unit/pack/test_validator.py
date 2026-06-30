# Pack 测试——validator schema / loader / Pack tests — validator + loader
"""Pack 测试——validator schema / loader."""

import pytest  # 测试框架
from pydantic import ValidationError  # 校验异常

from src.pack.loader import WorldLoader
from src.pack.validator import (
    FilesManifest,
    MetaYaml,
    PackValidator,
    SpriteConfig,
    StartingActor,
    StartingPc,
    StartingSceneObject,
)


class TestSpriteConfig:
    def test_defaults(self):
        sc = SpriteConfig()
        assert sc.frame_size == 48
        assert sc.directions == 4
        assert sc.frames_per_direction == 4


class TestFilesManifest:
    def test_defaults(self):
        fm = FilesManifest()
        assert fm.story_setup == "story_setup.yaml"
        assert fm.lore == []

    def test_with_files(self):
        fm = FilesManifest(scenes=["scene_01.yaml"], actors=["guard.yaml"])
        assert len(fm.scenes) == 1
        assert len(fm.actors) == 1


class TestStartingPc:
    def test_requires_template(self):
        pc = StartingPc(template="fighter")
        assert pc.template == "fighter"
        assert pc.name is None

    def test_template_required(self):
        with pytest.raises(ValidationError):
            StartingPc()  # type: ignore


class TestStartingActor:
    def test_defaults(self):
        a = StartingActor(template="guard")
        assert a.count == 1

    def test_count(self):
        a = StartingActor(template="guard", count=3)
        assert a.count == 3


class TestStartingSceneObject:
    def test_requires_template_and_scene(self):
        so = StartingSceneObject(template="chest", scene="dungeon_01")
        assert so.position == {"x": 0, "y": 0}


class TestMetaYaml:
    def test_valid_meta(self):
        data = {
            "id": "test_world",
            "name": "Test World",
            "description": "A test pack",
            "files": {},
            "starting_pcs": [{"template": "fighter"}],
            "starting_actors": [{"template": "guard", "count": 2}],
            "starting_scene_objects": [],
        }
        meta = MetaYaml(**data)
        assert meta.id == "test_world"
        assert len(meta.starting_pcs) == 1
        assert len(meta.starting_actors) == 1

    def test_invalid_id(self):
        with pytest.raises(ValidationError):
            MetaYaml(id="123invalid")  # must start with lowercase letter


class TestPackValidator:
    def test_validate_returns_meta(self):
        data = {
            "id": "valid_pack",
            "name": "Valid Pack",
            "files": {},
        }
        meta = PackValidator.validate(data)
        assert isinstance(meta, MetaYaml)
        assert meta.id == "valid_pack"

    def test_validate_invalid_raises(self):
        with pytest.raises(ValidationError):
            PackValidator.validate({"id": "bad", "name": 123})  # name should be str


class TestWorldLoader:
    def test_loader_exists(self):
        assert WorldLoader is not None

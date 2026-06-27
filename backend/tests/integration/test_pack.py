"""Test World Pack loading – M2."""

import tempfile
from pathlib import Path

import pytest

from src.storage import ChromaManager
from src.pack import WorldLoader

PACK_DIR = Path(__file__).resolve().parents[3] / "worlds"


class TestWorldLoader:
    """Integration test: load forgotten_realms pack and verify WorldState."""

    def test_load_forgotten_realms(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            chroma = ChromaManager(Path(tmpdir))
            loader = WorldLoader(PACK_DIR, chroma)

            ws = loader.load("forgotten_realms")

            # Basic world info
            assert ws.current_world == "forgotten_realms"
            assert ws.current_scene == "village_elderwood"
            assert ws.tick == 0

            # 4 PCs loaded
            assert len(ws.player_characters) == 4
            kael = ws.player_characters["kael"]
            assert kael.name == "Kael"
            assert kael.role == "fighter"
            assert kael.combat.hp == 32
            assert kael.equipment.weapon == "longsword"
            assert len(kael.character_arc.growth_line) > 0

            # Zeph the rogue
            zeph = ws.player_characters["zeph"]
            assert zeph.attributes.dexterity == 18

            # 4 Actors loaded (Garret + Borin + Dane + Selia)
            assert len(ws.actors) == 4
            garret = ws.actors["garret"]
            assert garret.role == "blacksmith"
            assert "merchant" in [f.value for f in garret.functions]

            # Items loaded
            assert "longsword" in ws.items
            assert ws.items["longsword"].item_type.value == "weapon"
            assert ws.items["health_potion"].item_type.value == "potion"

            # Scene objects loaded
            assert len(ws.scene_objects) == 2
            chest = ws.scene_objects["village_elderwood_chest_wooden"]
            assert chest.object_type.value == "container"

            # Story loaded
            assert len(ws.story_arcs) == 1
            assert ws.story_arcs[0].title == "Bandit Threat"
            assert len(ws.story_hooks) == 2

    def test_lore_pumping(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            chroma = ChromaManager(Path(tmpdir))
            loader = WorldLoader(PACK_DIR, chroma)

            pack_dir = PACK_DIR / "forgotten_realms"
            loader.pump_lore(pack_dir, "forgotten_realms")

            results = chroma.query_lore("forgotten_realms", "village border", top_k=3)
            assert len(results) > 0

    def test_meta_validation(self):
        from src.pack.validator import PackValidator, MetaYaml

        meta = PackValidator.validate({
            "id": "test_world",
            "name": "Test World",
            "starting_scene": "test_village",
        })
        assert meta.id == "test_world"
        assert meta.rule_set == "dnd_5e_srd"

    def test_missing_pack_raises(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            chroma = ChromaManager(Path(tmpdir))
            loader = WorldLoader(PACK_DIR, chroma)
            with pytest.raises(FileNotFoundError):
                loader.load("nonexistent_pack")

    def test_missing_meta_raises(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            chroma = ChromaManager(Path(tmpdir))
            empty_dir = Path(tmpdir) / "broken_pack"
            empty_dir.mkdir()
            loader = WorldLoader(Path(tmpdir), chroma)
            with pytest.raises(FileNotFoundError):
                loader.load("broken_pack")

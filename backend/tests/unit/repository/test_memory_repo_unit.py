"""MemoryRepo 单元测试——Mock ChromaClient."""

from unittest.mock import Mock

from src.repository.memory_repo import MemoryRepo
from src.schemas.memory_schema import importance_of


class TestMemoryRepoUnit:
    """Mock ChromaClient 的 MemoryRepo 单元测试."""

    # 短期记忆应保留基本字段 / Short-term memory should keep core fields
    def test_store_short_term(self):
        repo = MemoryRepo(Mock())
        mem = repo.store("alex", "Found a rusty sword.", tick=1, importance=5)
        assert mem.pc_id == "alex"
        assert mem.importance == 5
        assert repo.count("alex") == 1

    def test_short_term_max_10(self):
        repo = MemoryRepo(Mock())
        for i in range(15):
            repo.store("alex", f"Memory {i}", tick=i)
        assert repo.count("alex") == 10

    def test_importance_should_reflect(self):
        repo = MemoryRepo(Mock())
        repo.store("alex", "Big fight!", tick=0, importance=50)
        repo.store("alex", "Another fight!", tick=1, importance=60)
        assert repo.importance_should_reflect("alex", threshold=100)

    def test_importance_should_not_reflect(self):
        repo = MemoryRepo(Mock())
        repo.store("alex", "Walked around.", tick=0, importance=2)
        assert not repo.importance_should_reflect("alex", threshold=100)

    def test_drop_character_clears(self):
        repo = MemoryRepo(Mock())
        repo.store("alex", "test", tick=0)
        repo.drop_character("alex")
        assert repo.count("alex") == 0

    def test_count_unknown_character(self):
        repo = MemoryRepo(Mock())
        assert repo.count("nobody") == 0


class TestImportanceOf:
    def test_combat_hit(self):
        assert importance_of("combat_hit") == 8

    def test_character_death(self):
        assert importance_of("character_death") == 10

    def test_move(self):
        assert importance_of("move") == 1

    def test_unknown_type_default(self):
        assert importance_of("unknown_event") == 2

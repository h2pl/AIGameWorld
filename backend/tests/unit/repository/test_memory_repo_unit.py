"""MemoryRepo 单元测试——Mock ChromaClient."""

from unittest.mock import Mock

import pytest

from src.domain.memory import MemoryType, importance_of
from src.repository.memory_repo import MemoryRepo


class TestMemoryRepoUnit:
    """Mock ChromaClient 的 MemoryRepo 单元测试."""

    @pytest.mark.asyncio
    async def test_store_short_term(self):
        repo = MemoryRepo(Mock())
        mem = await repo.store("alex", "Found a rusty sword.", tick=1, importance=5)
        assert mem.pc_id == "alex"
        assert mem.importance == 5
        assert repo.count("alex") == 1

    @pytest.mark.asyncio
    async def test_short_term_max_10(self):
        repo = MemoryRepo(Mock())
        for i in range(15):
            await repo.store("alex", f"Memory {i}", tick=i)
        assert repo.count("alex") == 10

    @pytest.mark.asyncio
    async def test_importance_should_reflect(self):
        repo = MemoryRepo(Mock())
        await repo.store("alex", "Big fight!", tick=0, importance=50)
        await repo.store("alex", "Another fight!", tick=1, importance=60)
        assert repo.importance_should_reflect("alex", threshold=100)

    @pytest.mark.asyncio
    async def test_importance_should_not_reflect(self):
        repo = MemoryRepo(Mock())
        await repo.store("alex", "Walked around.", tick=0, importance=2)
        assert not repo.importance_should_reflect("alex", threshold=100)

    @pytest.mark.asyncio
    async def test_drop_character_clears(self):
        repo = MemoryRepo(Mock())
        await repo.store("alex", "test", tick=0)
        await repo.drop_character("alex")
        assert repo.count("alex") == 0

    def test_count_unknown_character(self):
        repo = MemoryRepo(Mock())
        assert repo.count("nobody") == 0


class TestImportanceOf:
    def test_combat(self):
        assert importance_of(MemoryType.COMBAT.value) == 8

    def test_reflection(self):
        assert importance_of(MemoryType.REFLECTION.value) == 10

    def test_talk(self):
        assert importance_of(MemoryType.TALK.value) == 3

    def test_explore(self):
        assert importance_of(MemoryType.EXPLORE.value) == 2

    def test_interact(self):
        assert importance_of(MemoryType.INTERACT.value) == 4

    def test_observation(self):
        assert importance_of(MemoryType.OBSERVATION.value) == 1

    def test_unknown_type_default(self):
        assert importance_of("unknown_event") == 2

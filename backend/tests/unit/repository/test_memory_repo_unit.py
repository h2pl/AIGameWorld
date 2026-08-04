"""MemoryRepo 单元测试——Mock ChromaClient."""

from unittest.mock import Mock

import pytest

from src.domain.memory import MemoryType, importance_of
from src.repository.memory_repo import MemoryRepo


class TestMemoryRepoUnit:
    """Mock ChromaClient 的 MemoryRepo 单元测试."""

    @pytest.mark.asyncio
    async def test_store_returns_memory(self):
        repo = MemoryRepo(Mock())
        mem = await repo.store("alex", "Found a rusty sword.", tick=1, importance=5)
        assert mem.pc_id == "alex"
        assert mem.importance == 5
        assert mem.content == "Found a rusty sword."

    @pytest.mark.asyncio
    async def test_store_calls_chroma(self):
        chroma = Mock()
        repo = MemoryRepo(chroma)
        await repo.store("alex", "test", tick=1)
        chroma.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_no_sqlite(self):
        repo = MemoryRepo(Mock())
        result = await repo.get_recent("alex")
        assert result == []

    @pytest.mark.asyncio
    async def test_importance_should_reflect_no_sqlite(self):
        repo = MemoryRepo(Mock())
        assert not await repo.importance_should_reflect("alex", threshold=100)


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

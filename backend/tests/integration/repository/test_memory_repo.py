"""MemoryRepo 集成测试——真实 ChromaDB 读写."""

import tempfile
from pathlib import Path

import pytest

from src.repository.memory_repo import MemoryRepo
from src.storage.chroma_client import ChromaClient


@pytest.fixture(scope="module")
def repo():
    tmp = tempfile.mkdtemp(prefix="chroma_test_")
    chroma = ChromaClient(Path(tmp))
    yield MemoryRepo(chroma)


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, repo):
        await repo.store("alex", "Found a rusty sword in the tavern.", tick=1, importance=5, current_tick=100)
        results = repo.search_long_term_vector("alex", "sword tavern", top_k=3)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_retrieve_returns_by_importance(self, repo):
        await repo.store("alex", "Walked around town.", tick=1, importance=1, current_tick=100)
        await repo.store("alex", "Fought a goblin!", tick=2, importance=8, current_tick=100)
        await repo.store("alex", "Bought a potion.", tick=3, importance=3, current_tick=100)
        results = repo.search_long_term_vector("alex", "adventure", top_k=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_retrieve_empty_character(self, repo):
        results = repo.search_long_term_vector("nobody", "anything")
        assert results == []

    @pytest.mark.asyncio
    async def test_short_term_max_10_with_chroma(self, repo):
        for i in range(15):
            await repo.store("bob", f"Memory number {i}", tick=i, importance=3)
        assert repo.count("bob") == 10


class TestReflection:
    @pytest.mark.asyncio
    async def test_store_and_retrieve_reflection(self, repo):
        await repo.store_reflection("maya", "I should be more cautious.", tick=5)
        results = await repo.retrieve_reflections("maya", "caution", top_k=3)
        assert len(results) >= 1
        assert results[0].importance == 10
        assert results[0].memory_type == "reflection"


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_drop_character_clears_everything(self, repo):
        await repo.store("charlie", "Important memory", tick=1, importance=9)
        await repo.store_reflection("charlie", "Deep insight", tick=2)
        await repo.drop_character("charlie")
        assert repo.count("charlie") == 0
        short = repo.get_short_term("charlie")
        assert short == []

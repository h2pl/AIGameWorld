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
    # cleanup handled by tempfile on exit


class TestMemoryStore:
    def test_store_and_retrieve(self, repo):
        repo.store("alex", "Found a rusty sword in the tavern.", tick=1, importance=5)
        results = repo.retrieve("alex", "sword tavern", top_k=3)
        assert len(results) >= 1
        assert "sword" in results[0].content or "tavern" in results[0].content

    def test_retrieve_returns_by_importance(self, repo):
        repo.store("alex", "Walked around town.", tick=1, importance=1)
        repo.store("alex", "Fought a goblin!", tick=2, importance=8)
        repo.store("alex", "Bought a potion.", tick=3, importance=3)
        results = repo.retrieve("alex", "adventure", top_k=5)
        assert results[0].importance == 8

    def test_retrieve_empty_character(self, repo):
        results = repo.retrieve("nobody", "anything")
        assert results == []

    def test_short_term_max_10_with_chroma(self, repo):
        for i in range(15):
            repo.store("bob", f"Memory number {i}", tick=i, importance=3)
        assert repo.count("bob") == 10


class TestReflection:
    def test_store_and_retrieve_reflection(self, repo):
        repo.store_reflection("maya", "I should be more cautious.", tick=5)
        results = repo.retrieve_reflections("maya", "caution", top_k=3)
        assert len(results) >= 1
        assert results[0].importance == 10
        assert results[0].memory_type == "reflection"


class TestLifecycle:
    def test_drop_character_clears_everything(self, repo):
        repo.store("charlie", "Important memory", tick=1, importance=9)
        repo.store_reflection("charlie", "Deep insight", tick=2)
        repo.drop_character("charlie")
        assert repo.count("charlie") == 0
        assert repo.retrieve("charlie", "memory") == []

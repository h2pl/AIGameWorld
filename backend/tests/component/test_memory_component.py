"""Memory 组件测试——短期 deque + 长期 ChromaDB 协作."""
import tempfile
from pathlib import Path

import pytest

from src.repository.memory_repo import MemoryRepo
from src.storage.chroma_client import ChromaClient


@pytest.fixture(scope="module")
def repo():
    tmp = tempfile.mkdtemp(prefix="chroma_comp_")
    chroma = ChromaClient(Path(tmp))
    return MemoryRepo(chroma)


def test_short_and_long_term_merged(repo):
    """短期(deque)和长期(ChromaDB)合并去重."""
    # use unique character per test to avoid cross-contamination
    repo.store("test_merge", "Short term only", tick=1, importance=3)
    repo.store("test_merge", "Also in chroma", tick=2, importance=6)
    results = repo.retrieve("test_merge", "term chroma", top_k=5)
    assert len(results) >= 1
    assert results[0].importance >= results[-1].importance


def test_multi_character_isolation(repo):
    """多个角色的记忆互不干扰."""
    repo.store("alex_iso", "Alex memory", tick=1)
    repo.store("maya_iso", "Maya memory", tick=1)
    alex = repo.retrieve("alex_iso", "memory", top_k=5)
    maya = repo.retrieve("maya_iso", "memory", top_k=5)
    assert len(alex) >= 1
    assert len(maya) >= 1
    assert "Alex" in alex[0].content
    assert "Maya" in maya[0].content


def test_reflection_independent_from_memory(repo):
    """反思记忆独立于普通记忆."""
    repo.store("alex_refl", "Regular memory", tick=1, importance=5)
    repo.store_reflection("alex_refl", "Deep insight about trust", tick=2)
    reflections = repo.retrieve_reflections("alex_refl", "trust", top_k=5)
    assert len(reflections) >= 1
    assert all(r.memory_type == "reflection" for r in reflections)
